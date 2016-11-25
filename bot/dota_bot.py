import math
import random
import logging
from threading import Thread
import gevent
import pickle
from datetime import datetime, timedelta
from eventemitter import EventEmitter
from sqlalchemy.orm import joinedload_all

from steam import SteamClient, SteamID
import dota2
from dota2.enums import DOTA_GC_TEAM, EMatchOutcome

from web.web_application import create_app

from common.models import db, User, Match, PlayerInMatch
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

        self.match = None
        self.players = None

        self.game_status = None
        self.invite_timer = None
        self.missing_players = None
        self.wrong_team_players = None

    # Manage Clients

    def print_error(self, result):
        logging.error("Error: %s", result)

    def reconnect_bot(self):
        logging.info('disconnected')
        self.job_ready = False
        self.client.connect(retry=None)

    def login_bot(self):
        logging.info('connected')
        self.client.login(self.login, self.password)

    def start_dota(self):
        logging.info('logged')
        self.dota.launch()

    def start_processing(self):
        logging.info('dota ready')
        self.job_ready = True

    def stop_processing(self):
        logging.info('dota notready')
        self.job_ready = False

    # Work with jobs

    def new_job(self):
        logging.info('Processing new job of type %s', self.current_job.type)
        self.job_ready = False

        if self.current_job.type == JobType.ScanProfile:
            self.dota.emit('scan_profile')
        elif self.current_job.type == JobType.VIPGame:
            self.dota.emit('vip_game')
        else:
            self.end_job_processing(True)

    def end_job_processing(self, ack):
        logging.info('Job ended.')
        if ack:
            self.queue.ack_last()
        self.job_ready = True
        self.current_job = None

    # Scan profile

    def scan_profile(self):
        while not self.current_job.scan_finish:
            logging.info('Requesting profile for user %s' % self.current_job.steam_id)
            user = SteamID(self.current_job.steam_id)
            self.dota.request_profile_card(user.as_32)

            # We give the task 30 sec to finish or retry
            gevent.sleep(30)

        if self.current_job.scan_finish:
            self.end_job_processing(True)

    def scan_profile_result(self, account_id, profile_card):
        logging.info('Processing profile of user %s' % account_id)
        solo_mmr = None
        for slot in profile_card.slots:
            if not slot.HasField('stat'):
                continue
            if slot.stat.stat_id != 1:
                continue
            solo_mmr = int(slot.stat.stat_score)

        with self.app.app_context():
            user = User.query.filter_by(id=self.current_job.steam_id).first()
            user.profile_scan_info.last_scan = datetime.utcnow()

            if solo_mmr is not None:
                user.solo_mmr = solo_mmr
                if user.solo_mmr > 5000:
                    user.give_permission(constants.PERMISSION_PLAY_VIP, True)
                    if user.vip_mmr is None:
                        user.vip_mmr = 2000 + math.floor((user.solo_mmr - 5000)/2)
            db.session.commit()
        self.current_job.scan_finish = True

    # Manage games

    def vip_game(self):
        logging.info('Hosting game %s' % self.current_job.match_id)
        with self.app.app_context():
            self.match = Match.query.filter_by(id=self.current_job.match_id).first()
            if self.match is None or self.match.status != constants.MATCH_STATUS_CREATION:
                self.end_job_processing(True)
            else:
                self.players = {}
                for player in PlayerInMatch.query.\
                    options(joinedload_all('player')).\
                    filter(PlayerInMatch.match_id == self.current_job.match_id).\
                    all():
                    self.players[player.player_id] = player

                db.session.expunge(self.match)
                for player_id, player in self.players.items():
                    db.session.expunge(player)
                self.dota.create_practice_lobby(password=self.match.password)

    def vip_game_created(self, message):
        self.game_status = message

        if self.current_job is None:
            self.dota.leave_practice_lobby()
        else:
            # Create game and setup
            logging.info('Game %s created, setup.' % self.current_job.match_id)
            self.dota.join_practice_lobby_team()
            options = {
                'game_name': 'Dazzar Game {0}'.format(str(self.match.id)),
                'pass_key': self.match.password,
                'game_mode': dota2.enums.DOTA_GameMode.DOTA_GAMEMODE_RD,
                'server_region': int(dota2.enums.EServerRegion.Europe),
                'fill_with_bots': False,
                'allow_spectating': True,
                'allow_cheats': False,
                'allchat': False,
                'dota_tv_delay': 2,
                'pause_setting': 1
            }
            self.dota.config_practice_lobby(options=options)
            with self.app.app_context():
                match = Match.query.filter_by(id=self.current_job.match_id).first()
                match.status = constants.MATCH_STATUS_WAITING_FOR_PLAYERS
                db.session.commit()

            # Wait for players
            self.invite_timer = timedelta(minutes=5)
            self.compute_missing_players()
            start = False
            refresh_rate = 10
            while self.invite_timer != timedelta(0):
                for player in self.missing_players:
                    self.dota.invite_to_lobby(player)
                gevent.sleep(refresh_rate)
                self.compute_missing_players()

                if len(self.missing_players) == 0 and len(self.wrong_team_players) == 0:
                    start = True
                    break
                else:
                    # Say: Joueurs manquants self.missing_players
                    # Say: Joueurs dans les mauvaises équipes self.wrong_team_players
                    # Say: Temps restant avant lancement: self.invite_timer
                    logging.error('Missing players %s', self.missing_players)
                    logging.error('Wrong team players %s', self.wrong_team_players)
                    self.invite_timer = self.invite_timer - timedelta(seconds=refresh_rate)

            if not start:
                # Say: Partie annulée - punish
                with self.app.app_context():
                    match = Match.query.filter_by(id=self.current_job.match_id).first()
                    match.status = constants.MATCH_STATUS_CANCELLED
                    for player in PlayerInMatch.query. \
                            options(joinedload_all('player')). \
                            filter(PlayerInMatch.match_id == self.current_job.match_id). \
                            all():
                        if player.player.current_match == self.current_job.match_id:
                            player.player.current_match = None
                        if player.player_id in self.missing_players or player.player_id in self.wrong_team_players:
                            player.mmr_after = max(player.mmr_before - 150, 0)
                            player.player.vip_mmr = player.mmr_after
                        else:
                            player.mmr_after = player.mmr_before
                    db.session.commit()
                self.dota.leave_practice_lobby()
            else:
                # Start the game and manage status
                self.dota.launch_practice_lobby()
                with self.app.app_context():
                    match = Match.query.filter_by(id=self.current_job.match_id).first()
                    match.status = constants.MATCH_STATUS_IN_PROGRESS
                    db.session.commit()
                gevent.sleep(30)

                # PostGame = 3 & UI = 0 (means no loading)
                while self.game_status.state != 0 and self.game_status.state != 3:
                    gevent.sleep(5)

                with self.app.app_context():
                    match = Match.query.filter_by(id=self.current_job.match_id).first()
                    if self.game_status.state == 0:
                        # state UI = 0, punish not loaded
                        match.status = constants.MATCH_STATUS_CANCELLED
                        self.compute_missing_players()
                        for player in PlayerInMatch.query. \
                                options(joinedload_all('player')). \
                                filter(PlayerInMatch.match_id == self.current_job.match_id). \
                                all():
                            if player.player.current_match == self.current_job.match_id:
                                player.player.current_match = None
                            player.mmr_after = player.mmr_before
                            if player.player_id in self.missing_players or player.player_id in self.wrong_team_players:
                                player.mmr_after = max(player.mmr_before - 150, 0)
                    elif self.game_status.state == 3:
                        # state POSTGAME = 3, report result and leavers
                        match.status = constants.MATCH_STATUS_ENDED

                        self.players = {}
                        for player in PlayerInMatch.query. \
                                options(joinedload_all('player')). \
                                filter(PlayerInMatch.match_id == self.current_job.match_id). \
                                all():
                            if player.player.current_match == self.current_job.match_id:
                                player.player.current_match = None
                            player.mmr_after = player.mmr_before
                            self.players[player.player_id] = player
                        for player in self.game_status.members:
                            if player.id == self.dota.steam_id:
                                continue
                            id = player.id
                            if (self.players[id].is_radiant and self.game_status.match_outcome == 2) or \
                               (not self.players[id].is_radiant and self.game_status.match_outcome == 3):
                                self.players[id].mmr_after = self.players[id].mmr_before + 50
                            elif (self.players[id].is_radiant and self.game_status.match_outcome == 3) or \
                               (not self.players[id].is_radiant and self.game_status.match_outcome == 2):
                                self.players[id].mmr_after = max(self.players[id].mmr_before - 50, 0)
                        for player in self.game_status.left_members:
                            self.players[player.id].mmr_after = max(self.players[player.id].mmr_before-300, 0)
                        for player_id, player in self.players.items():
                            player.player.vip_mmr = player.mmr_after
                    db.session.commit()

            self.dota.leave_practice_lobby()
            self.end_job_processing(True)

    def game_update(self, message):
        self.game_status = message
        logging.error('%s', message)

    def compute_missing_players(self):
        self.missing_players = []
        self.wrong_team_players = []

        for player_id, player in self.players.items():
            self.missing_players.append(player_id)

        for message_player in self.game_status.members:
            if message_player.id == self.dota.steam_id:
                continue
            if message_player.id in self.missing_players:
                self.missing_players.remove(message_player.id)
                good_slot = message_player.slot == self.players[message_player.id].team_slot
                good_team = (message_player.team == DOTA_GC_TEAM.GOOD_GUYS and
                             self.players[message_player.id].is_radiant) or \
                            (message_player.team == DOTA_GC_TEAM.BAD_GUYS and
                             not self.players[message_player.id].is_radiant)
                if not (good_team and good_slot):
                    self.wrong_team_players.append(message_player.id)
                    if message_player.team != DOTA_GC_TEAM.PLAYER_POOL:
                        self.dota.practice_lobby_kick_from_team(SteamID(message_player.id).as_32)
            else:
                # Say: Kick joueur non authorisé message_player.name
                self.dota.practice_lobby_kick(SteamID(message_player.id).as_32)

    # Main run
    def run(self):
        self.client = SteamClient()
        self.dota = dota2.Dota2Client(self.client)
        self.dota.verbose_debug = True
        self.app = create_app()
        self.queue = QueueAdapter(self.app.config['RABBITMQ_LOGIN'], self.app.config['RABBITMQ_PASSWORD'])

        self.client.on('connected', self.login_bot)
        self.client.on('disconnected', self.reconnect_bot)
        self.client.on('logged_on', self.start_dota)
        self.client.on('error', self.print_error)

        self.dota.on('error', self.print_error)
        self.dota.on('ready', self.start_processing)
        self.dota.on('notready', self.stop_processing)
        self.dota.on('new_job', self.new_job)

        self.dota.on('scan_profile', self.scan_profile)
        self.dota.on('profile_card', self.scan_profile_result)

        self.dota.on('vip_game', self.vip_game)
        self.dota.on(dota2.features.Lobby.EVENT_LOBBY_NEW, self.vip_game_created)
        self.dota.on(dota2.features.Lobby.EVENT_LOBBY_CHANGED, self.game_update)

        self.client.connect(retry=None, delay=random.randint(1, 20))

        while True:
            # Get jobs if ready
            self.queue.refresh()

            if self.job_ready and self.current_job is None:
                message = self.queue.consume()
                if message is not None:
                    self.current_job = pickle.loads(message)
                    self.dota.emit('new_job')

            gevent.sleep(20 + random.randint(0, 10))
