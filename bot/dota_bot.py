import logging, sys
from threading import Thread
import gevent
import pickle
from datetime import datetime

from eventemitter import EventEmitter

from steam import SteamClient, SteamID
from steam.enums import EResult

from dota2 import Dota2Client

from web.web_application import create_app

from common.models import db, User
from common.job_queue import QueueAdapter, Job, JobType
import common.constants as constants


class DotaBotThread(EventEmitter, Thread):
    """A worker thread, connected to steam and processing jobs.
    """
    def __init__(self, login, password):
        self.login = login
        self.password = password

        Thread.__init__(self, name=self.login)

        self.client = None
        self.dota = None
        self.app = None
        self.queue = None

        self.job_ready = False
        self.current_job = None

    def print_error(self, result):
        logging.error("Error: %s", result)

    def login_bot(self):
        logging.info('connected')
        self.client.login(self.login, self.password)

    def start_dota(self):
        logging.info('logged')
        self.dota.launch()

    def start_processing(self):
        logging.info('dota ready')
        self.job_ready = True

    def new_job(self):
        logging.info('Processing new job of type %s', self.current_job.type)
        self.job_ready = False
        if self.current_job.type == JobType.ScanProfile:
            self.dota.emit('scan_profile')
        else:
            self.end_job_processing(False)

    def scan_profile(self):
        while self.current_job is not None:
            user = SteamID(self.current_job.steam_id)
            self.dota.request_profile_card(user.as_32)

            # We give the task 30 sec to finish or retry
            gevent.sleep(30)
            if self.current_job is None:
                self.job_ready = True

    def scan_profile_result(self, account_id, profile_card):
        solo_mmr = None
        for slot in profile_card.slots:
            if not slot.HasField('stat'):
                continue
            if slot.stat.stat_id != 1:
                continue
            solo_mmr = int(slot.stat.stat_score)

        with self.app.app_context():
            user = User.query.filter_by(id=self.current_job.steam_id).first()
            user.last_scan = datetime.utcnow()

            if solo_mmr is not None:
                user.solo_mmr = solo_mmr
                if user.solo_mmr > 5000:
                    user.give_permission(constants.PERMISSION_PLAY_VIP, True)
            db.session.commit()

        self.end_job_processing(True)

    def end_job_processing(self, ack):
        logging.info('Job ended.')
        if ack:
            self.queue.ack_last()
        self.current_job = None

    def run(self):
        self.client = SteamClient()
        self.dota = Dota2Client(self.client)
        self.app = create_app()
        self.queue = QueueAdapter()

        self.client.on('connected', self.login_bot)
        self.client.on('logged_on', self.start_dota)
        self.client.on('error', self.print_error)

        self.dota.on('error', self.print_error)
        self.dota.on('ready', self.start_processing)
        self.dota.on('new_job', self.new_job)
        self.dota.on('scan_profile', self.scan_profile)
        self.dota.on('profile_card', self.scan_profile_result)

        self.client.connect(retry=1)

        while True:
            if self.job_ready and self.current_job is None:
                message = self.queue.consume()
                if message is not None:
                    self.current_job = pickle.loads(message)
                    self.dota.emit('new_job')

            gevent.sleep(5)
