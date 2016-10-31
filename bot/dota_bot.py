import logging, sys
from time import sleep
from threading import Thread
import pika

from steam import SteamClient, SteamID
from steam.enums import EResult

from dota2 import Dota2Client

from web.web_application import create_app
from common.models import db, User, MMRChecker
from common.job_queue import QueueAdapter
import common.constants as constants


class DotaBotThread(Thread):
    """A worker thread, connected to steam and processing jobs.
    """

    def __init__(self):
        Thread.__init__(self, name='DotaBot0')
        self.dota = None

    def callback(self, ch, method, properties, body):
        logging.info(" [x] Received %r" % body)
        ch.basic_ack(delivery_tag=method.delivery_tag)

    def run(self):
        client = SteamClient()
        dota = Dota2Client(client)
        app = create_app()
        self.dota = dota

        self.queue = QueueAdapter()
        self.queue.consume_forever(self.callback)

        @client.on('error')
        def print_error(result):
            logging.error("Error: {0}".format(EResult(result)))

        @client.on('connected')
        def login():
            logging.info('connected')
            client.login(app.config['STEAM_BOT{0}_LOGIN'.format(0)], app.config['STEAM_BOT{0}_PASSWORD'.format(0)])

        @client.on('disconnected')
        def quit():
            sys.exit(0)

        @client.on('logged_on')
        def start_dota():
            logging.info('logged')
            dota.launch()

        @dota.on('ready')
        def dota_ready():
            pass

        @self.dota.on('fetch_profile')
        def fetch_profile_card():
            logging.info('toto')
            with app.app_context():
                request = MMRChecker.query.first()
                if request is None:
                    return
                user = SteamID(request.id)
                dota.request_profile_card(user.as_32)

        @dota.on('profile_card')
        def print_profile_card(account_id, profile_card):
            solo_mmr = 0
            for slot in profile_card.slots:
                if not slot.HasField('stat'):
                    continue
                if slot.stat.stat_id != 1:
                    continue
                solo_mmr = slot.stat.stat_score

            with app.app_context():
                if solo_mmr > 5000:
                    pass
                else:
                    user = SteamID(account_id)
                    request = MMRChecker.query.filter_by(id=str(user.as_64)).first()
                    if request is None:
                        return
                    request.status = constants.JOB_STEAM_STATUS_SOLO_MMR_REFUSED
                    db.session.commit()

        client.connect()
        client.run_forever()
        dota.emit('fetch_profile')
