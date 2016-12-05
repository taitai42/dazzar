import logging
from gevent import Greenlet, sleep
from datetime import datetime, timedelta
from eventemitter import EventEmitter

from sqlalchemy.orm import joinedload_all
from steam import SteamClient, SteamID
import dota2
from dota2.enums import DOTA_GC_TEAM, EMatchOutcome

from web.web_application import create_app
from common.models import db, User, Match, PlayerInMatch, Scoreboard
from common.job_queue import Job, JobScan, JobCreateGame
import common.constants as constants


class DotaBot(Greenlet, EventEmitter):
    """A worker thread, connecting to steam to process a unique job.

    Attributes:
        worker_manager: `DazzarWorkerManager` this bot is linked to.
        credential: `Credential` used to connect to steam.
    """

    def __init__(self, worker_manager, credential, job):
        """Initialize the Dota bot thread for a unique job process.

        Args:
            worker_manager: `DazzarWorkerManager` this bot is linked to.
            credential: `Credential` used to connect to steam.
            job: `Job` to process by the bot.
        """
        Greenlet.__init__(self)

        self.credential = credential
        self.worker_manager = worker_manager
        self.job = job

        self.client = SteamClient()
        self.dota = dota2.Dota2Client(self.client)
        self.app = create_app()

        self.job_started = False
        self.job_finished = False

        self.match = None
        self.players = None

        self.game_status = None
        self.invite_timer = None
        self.missing_players = None
        self.wrong_team_players = None

        # Prepare all event handlers
        # - Steam client events
        # - Dota client events
        # - Dazzar bot events
        self.client.on('connected', self.steam_connected)
        self.client.on('logged_on', self.steam_logged)

        self.dota.on('ready', self.dota_ready)
        self.dota.on('notready', self.closed_dota)

        self.dota.on('profile_card', self.scan_profile_result)
        self.dota.on(dota2.features.Lobby.EVENT_LOBBY_NEW, self.vip_game_created)
        self.dota.on(dota2.features.Lobby.EVENT_LOBBY_CHANGED, self.game_update)

    def _run(self):
        """Start the main loop of the thread, connecting to Steam, waiting for the job to finish to close the bot."""
        self.print_info('Connecting to Steam...')
        self.client.connect(retry=None)  # Try connecting with infinite retries

        while not self.job_finished:
            sleep(10)

        self.client.disconnect()
        self.worker_manager.bot_end(self.credential)

    # Helpers

    def print_info(self, trace):
        """Wrapper of `logging.info` with bot name prefix.

        Args:
            trace: String to output as INFO.
        """
        logging.info('%s: %s', self.credential.login, trace)

    def print_error(self, trace):
        """Wrapper of `logging.error` with bot name prefix.

        Args:
            trace: String to output as ERROR.
        """
        logging.error("%s: %s", self.credential.login, trace)

    # Callback of Steam and Dota clients

    def steam_connected(self):
        """Callback fired when the bot is connected to Steam, login user."""
        self.print_info('Connected to Steam.')
        self.client.login(self.credential.login, self.credential.password)

    def steam_logged(self):
        """Callback fired when the bot is logged into Steam, starting Dota."""
        self.print_info('Logged to Steam.')
        self.dota.launch()

    def dota_ready(self):
        """Callback fired when the Dota application is ready, resume the job processing."""
        self.print_info('Dota application is ready.')
        self.compute_job()

    def closed_dota(self):
        """Callback fired when the Dota application is closed."""
        self.print_info('Dota application is closed.')

    def compute_job(self):
        """Start the processing of the job with the appropriate handler."""
        self.print_info('Processing new job of type %s' % type(self.job))
        if not self.job_started :
            self.job_started = True
        else:
            return

        if type(self.job) is JobScan:
            self.scan_profile()
        elif type(self.job) is JobCreateGame:
            self.vip_game()
        else:
            self.end_job_processing()

    def end_job_processing(self):
        """Mark the job as finished, preparing the bot to close."""
        self.print_info('Job ended.')
        self.job = None
        self.job_finished = True

    ############################
    # Scan profile job section #
    ############################

    def scan_profile(self):
        """Start the process of the job as a profile scan, request the information from Steam."""
        while not self.job.scan_finish:
            self.print_info('Requesting profile for user %s' % self.job.steam_id)
            user = SteamID(self.job.steam_id)
            self.dota.request_profile_card(user.as_32)

            # We give the task 30 sec to finish or retry
            sleep(30)

        if self.job.scan_finish:
            self.end_job_processing()

    def scan_profile_result(self, account_id, profile_card):
        """Process the profile information returned by Steam.

        Extract the SoloMMR from the profile and insert the user in the good ladder.

        Args:
            account_id: steam_id (as 32bits) of the profile result
            profile_card: profile information as a protobuff message
        """
        self.print_info('Processing profile of user %s' % SteamID(account_id).as_64)
        solo_mmr = None
        for slot in profile_card.slots:
            if not slot.HasField('stat'):
                continue
            if slot.stat.stat_id != 1:
                continue
            solo_mmr = int(slot.stat.stat_score)

        with self.app.app_context():
            user = User.query.filter_by(id=self.job.steam_id).first()
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
        self.job.scan_finish = True

    ########################
    # VIP game job section #
    ########################

    def vip_game(self):
        """Start the process of the job as a game creation."""
        self.print_info('Hosting game %s' % self.job.match_id)

        # Copy the match data from the database
        with self.app.app_context():
            self.match = Match.query.filter_by(id=self.job.match_id).first()
            if self.match is None or self.match.status != constants.MATCH_STATUS_CREATION:
                self.end_job_processing()
            else:
                self.players = {}
                for player in PlayerInMatch.query.\
                    options(joinedload_all('player')).\
                    filter(PlayerInMatch.match_id == self.job.match_id).\
                    all():
                    self.players[player.player_id] = player

                db.session.expunge(self.match)
                for player_id, player in self.players.items():
                    db.session.expunge(player)

        # Start the Dota lobby
        self.dota.create_practice_lobby(password=self.match.password)

    def vip_game_created(self, message):
        """Callback fired when the Dota bot enters a lobby.

        Args:
            message: first lobby information
        """
        self.game_status = message

        if self.job is None:
            self.dota.leave_practice_lobby()
        else:
            self.initialize_lobby()
            start = self.manage_player_waiting()

            if not start:
                self.process_game_dodge()
            else:
                self.start_game()

                # Waiting PostGame = 3 or UI = 0 (means no loading)
                while self.game_status.state != 0 and self.game_status.state != 3:
                    sleep(5)

                if self.game_status.state == 0:
                    self.process_game_dodge()
                elif self.game_status.state == 3:
                    self.process_endgame_results()

            self.dota.leave_practice_lobby()
            self.end_job_processing()

    def game_update(self, message):
        """Callback fired when the game lobby change, update local information."""
        self.game_status = message

    def initialize_lobby(self):
        """Setup the game lobby with the good options, and change status in database."""
        self.print_info('Game %s created, setup.' % self.job.match_id)
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
            match = Match.query.filter_by(id=self.job.match_id).first()
            match.status = constants.MATCH_STATUS_WAITING_FOR_PLAYERS
            db.session.commit()

    def manage_player_waiting(self):
        """Wait for players to join the lobby with actions depending on player actions.

        Returns:
            A boolean that indicates if the game should be started after the player waiting process.
        """
        self.invite_timer = timedelta(minutes=5)
        self.compute_player_status()
        refresh_rate = 10

        while self.invite_timer != timedelta(0):
            for player in self.missing_players:
                self.dota.invite_to_lobby(player)
            sleep(refresh_rate)
            self.compute_player_status()

            if len(self.missing_players) == 0 and len(self.wrong_team_players) == 0:
                return True
            else:
                # Say: Joueurs manquants self.missing_players
                # Say: Joueurs dans les mauvaises équipes self.wrong_team_players
                # Say: Temps restant avant lancement: self.invite_timer
                #  logging.error('Missing players %s', self.missing_players)
                # logging.error('Wrong team players %s', self.wrong_team_players)
                self.invite_timer = self.invite_timer - timedelta(seconds=refresh_rate)
        return False

    def compute_player_status(self):
        """Helpers to manage player status from protobuff message.

        Invite all missing players to come to the lobby.
        Kick all players not supposed to be inside a lobby.
        Kick from slots all players not in the good slot.
        """
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

    def process_game_dodge(self):
        """Punish players stopping game start."""
        self.print_info('Game %s cancelled because of dodge.' % self.job.match_id)

        # Say: Partie annulée - punish
        with self.app.app_context():
            match = Match.query.filter_by(id=self.job.match_id).first()
            match.status = constants.MATCH_STATUS_CANCELLED
            self.compute_player_status()
            for player in PlayerInMatch.query. \
                    options(joinedload_all('player')). \
                    filter(PlayerInMatch.match_id == self.job.match_id). \
                    all():
                if player.player.current_match == self.job.match_id:
                    player.player.current_match = None

                # Update Scoreboard
                if player.player_id in self.missing_players or player.player_id in self.wrong_team_players:
                    player.mmr_after = max(player.mmr_before - 150, 0)
                    player.is_dodge = True
                    score = Scoreboard.query.filter_by(ladder_name=match.section, user_id=player.player_id).first()
                    score.mmr = player.mmr_after
                    score.dodge += 1
                else:
                    player.mmr_after = player.mmr_before
            db.session.commit()

    def start_game(self):
        """Start the Dota game and update status in database."""
        self.print_info('Launching game %s' % self.job.match_id)

        self.dota.launch_practice_lobby()
        sleep(10)
        with self.app.app_context():
            match = Match.query.filter_by(id=self.job.match_id).first()
            match.status = constants.MATCH_STATUS_IN_PROGRESS
            if self.game_status.connect is not None and self.game_status.connect[0:1] == '=[':
                match.server = self.game_status.connect[2:-1]
            elif self.game_status.server_id is not None:
                match.server = self.game_status.server_id
            db.session.commit()
        sleep(10)

    def process_endgame_results(self):
        """After a game, process lobby results into database."""
        self.print_info('Game %s over.' % self.job.match_id)

        with self.app.app_context():
            match = Match.query.filter_by(id=self.job.match_id).first()
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
                    filter(PlayerInMatch.match_id == self.job.match_id). \
                    all():
                if player.player.current_match == self.job.match_id:
                    player.player.current_match = None
                player.mmr_after = player.mmr_before
                self.players[player.player_id] = player

            # Process scoreboard updates
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
                self.players[player.id].mmr_after = max(self.players[player.id].mmr_before - 300, 0)
                self.players[player.id].is_leaver = True
                score.leave += 1
            for player_id, player in self.players.items():
                score = Scoreboard.query.filter_by(ladder_name=match.section, user_id=player_id).first()
                score.mmr = player.mmr_after
                score.matches += 1
            db.session.commit()
