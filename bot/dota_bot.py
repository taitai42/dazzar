import random
import logging
from gevent import Greenlet, sleep
import pickle
from datetime import datetime, timedelta
from eventemitter import EventEmitter

from sqlalchemy.orm import joinedload_all
from steam import SteamClient, SteamID
import dota2
from dota2.enums import DOTA_GC_TEAM, EMatchOutcome

from web.web_application import create_app
from common.models import db, User, Match, PlayerInMatch, Scoreboard
from common.job_queue import QueueAdapter, Job, JobType
import common.constants as constants


class DotaBot(Greenlet, EventEmitter):
    """A worker thread, connected to steam and processing jobs.
    """
    def __init__(self, worker_manager, credential):
        Greenlet.__init__(self)

        self.credential = credential
        self.worker_manager = worker_manager

        self.login = self.credential.login
        self.password = self.credential.password

        self.client = None
        self.dota = None
        self.app = None

        self.current_job = None
        self.quit = False

        self.match = None
        self.players = None

        self.game_status = None
        self.invite_timer = None
        self.missing_players = None
        self.wrong_team_players = None

    # Manage Clients

    def print_info(self, trace):
        logging.info('%s: %s', self.login, trace)

    def print_error(self, trace):
        logging.error("%s: %s", self.login, trace)

    def login_bot(self):
        self.print_info('connected')
        self.client.login(self.login, self.password)

    def start_dota(self):
        self.print_info('logged')
        self.dota.launch()

    def start_processing(self):
        self.print_info('dota ready')
        self.worker_manager.emit('bot_started', self.credential)

    # Work with jobs

    def new_job(self, job):
        self.current_job = job
        self.print_info('Processing new job of type %s' % self.current_job.type)

        if self.current_job.type == JobType.ScanProfile:
            self.dota.emit('scan_profile')
        elif self.current_job.type == JobType.VIPGame:
            self.dota.emit('vip_game')
        else:
            self.end_job_processing(True)

    def end_job_processing(self, ack):
        self.print_info('Job ended.')
        self.current_job = None
        self.quit = True

    # Scan profile

    def scan_profile(self):
        while not self.current_job.scan_finish:
            self.print_info('Requesting profile for user %s' % self.current_job.steam_id)
            user = SteamID(self.current_job.steam_id)
            self.dota.request_profile_card(user.as_32)

            # We give the task 30 sec to finish or retry
            sleep(30)

        if self.current_job.scan_finish:
            self.end_job_processing(True)

    def scan_profile_result(self, account_id, profile_card):
        self.print_info('Processing profile of user %s' % account_id)
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
                    user.section = constants.LADDER_HIGH
                elif user.solo_mmr < 3000:
                    if user.section is None:
                        user.section = constants.LADDER_LOW
                else:
                    if user.section != constants.LADDER_HIGH:
                        user.section = constants.LADDER_MEDIUM

                scoreboard = Scoreboard.query.filter_by(user_id=user.id, ladder_name=user.section).first()
                if scoreboard is None:
                    scoreboard = Scoreboard(user, user.section)
                    db.session.add(scoreboard)
            db.session.commit()
        self.current_job.scan_finish = True

    # Manage games

    def vip_game(self):
        self.print_info('Hosting game %s' % self.current_job.match_id)
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
            self.print_info('Game %s created, setup.' % self.current_job.match_id)
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
                sleep(refresh_rate)
                self.compute_missing_players()

                if len(self.missing_players) == 0 and len(self.wrong_team_players) == 0:
                    start = True
                    break
                else:
                    # Say: Joueurs manquants self.missing_players
                    # Say: Joueurs dans les mauvaises équipes self.wrong_team_players
                    # Say: Temps restant avant lancement: self.invite_timer
                    # logging.error('Missing players %s', self.missing_players)
                    # logging.error('Wrong team players %s', self.wrong_team_players)
                    self.invite_timer = self.invite_timer - timedelta(seconds=refresh_rate)

            if not start:
                self.print_info('Game %s cancelled because of dodge.' % self.current_job.match_id)
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
                            player.is_dodge = True
                            score = Scoreboard.query.filter_by(ladder_name=match.section, user_id=player.player_id).first()
                            score.mmr = player.mmr_after
                            score.dodge += 1
                        else:
                            player.mmr_after = player.mmr_before
                    db.session.commit()
                self.dota.leave_practice_lobby()
            else:
                self.print_info('Launching game %s' % self.current_job.match_id)
                # Start the game and manage status
                self.dota.launch_practice_lobby()
                sleep(10)
                with self.app.app_context():
                    match = Match.query.filter_by(id=self.current_job.match_id).first()
                    match.status = constants.MATCH_STATUS_IN_PROGRESS
                    if self.game_status.connect is not None and self.game_status.connect[0:1] == '=[':
                        match.server = self.game_status.connect[2:-1]
                    elif self.game_status.server_id is not None:
                        match.server = self.game_status.server_id
                    db.session.commit()
                sleep(10)

                # PostGame = 3 & UI = 0 (means no loading)
                while self.game_status.state != 0 and self.game_status.state != 3:
                    sleep(5)

                with self.app.app_context():
                    match = Match.query.filter_by(id=self.current_job.match_id).first()
                    if self.game_status.state == 0:
                        self.print_info('Game %s cancelled because of no load.' % self.current_job.match_id)
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
                                player.is_dodge = True
                                score = Scoreboard.query.filter_by(ladder_name=match.section, user_id=player.player_id).first()
                                score.mmr = player.mmr_after
                                score.dodge += 1
                    elif self.game_status.state == 3:
                        # state POSTGAME = 3, report result and leavers
                        self.print_info('Game %s over.' % self.current_job.match_id)
                        match.status = constants.MATCH_STATUS_ENDED
                        match.server = None
                        if self.game_status.match_outcome == 2:
                            match.radiant_win = True
                        elif self.game_status.match_outcome == 3:
                            match.radiant_win = False
                        else:
                            match.radiant_win = None

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
                            score = Scoreboard.query.filter_by(ladder_name=match.section, user_id=id).first()
                            if (self.players[id].is_radiant and self.game_status.match_outcome == 2) or \
                               (not self.players[id].is_radiant and self.game_status.match_outcome == 3):
                                self.players[id].mmr_after = self.players[id].mmr_before + 50
                                score.win += 1
                            elif (self.players[id].is_radiant and self.game_status.match_outcome == 3) or \
                               (not self.players[id].is_radiant and self.game_status.match_outcome == 2):
                                self.players[id].mmr_after = max(self.players[id].mmr_before - 50, 0)
                                score.loss += 1
                        for player in self.game_status.left_members:
                            score = Scoreboard.query.filter_by(ladder_name=match.section, user_id=player.id).first()
                            self.players[player.id].mmr_after = max(self.players[player.id].mmr_before-300, 0)
                            self.players[player.id].is_leaver = True
                            score.leave += 1
                        for player_id, player in self.players.items():
                            score = Scoreboard.query.filter_by(ladder_name=match.section, user_id=player_id).first()
                            score.mmr = player.mmr_after
                            score.matches += 1
                    db.session.commit()

            self.dota.leave_practice_lobby()
            self.end_job_processing(True)

    def game_update(self, message):
        self.game_status = message

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
    def _run(self):
        self.client = SteamClient()
        self.dota = dota2.Dota2Client(self.client)
        self.app = create_app()

        self.on('new_job', self.new_job)

        self.client.on('connected', self.login_bot)
        self.client.on('logged_on', self.start_dota)
        self.client.on('error', self.print_error)

        self.dota.on('error', self.print_error)
        self.dota.on('ready', self.start_processing)

        self.dota.on('scan_profile', self.scan_profile)
        self.dota.on('profile_card', self.scan_profile_result)

        self.dota.on('vip_game', self.vip_game)
        self.dota.on(dota2.features.Lobby.EVENT_LOBBY_NEW, self.vip_game_created)
        self.dota.on(dota2.features.Lobby.EVENT_LOBBY_CHANGED, self.game_update)

        self.client.connect(retry=None, delay=random.randint(1, 5))

        while not self.quit:
            sleep(10)

        self.client.disconnect()
        self.worker_manager.emit('bot_end', self.credential)
