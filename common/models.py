from datetime import datetime
import string
import random

from flask_sqlalchemy import SQLAlchemy

import common.constants as constants

db = SQLAlchemy()

# Association of users to permissions
permissions = db.Table('permissions',
                       db.Column('permission_id', db.Integer(), db.ForeignKey('user_permission.id')),
                       db.Column('user_id', db.BigInteger(), db.ForeignKey('user.id')))


class User(db.Model):
    """A user representation in the database, linked to a Steam ID.

    Attributes:
        id: Unique Steam Id (as 64 bits).
        nickname: Unique nickname of the user, None when not setup.
        avatar: URL of the user avatar in steam, updated at each login (small).
        avatar_medium: URL of the user avatar in steam, updated at each login (medium).
        avatar_full: URL of the user avatar in steam, updated at each login (full).

        verified: Boolean True if the user is known in the community with this username.
        ban_date: Date the user is ban to.

        current_match: match_id of the match the user is currently in.
        solo_mmr: player solo mmr updated after a scan.
        section: ladder the user is playing in.

        scoreboards: ORM relation to the scoreboards of the user (in different ladders).
        user_permission: ORM relation to the permissions owned by the user.
        user_mix_detail: ORM relation to the player research by this user.
        profile_scan_info: ORM relation to the last Dota scan done.
        matches: ORM relation to all the matches played by this user.
    """
    __tablename__ = 'user'

    id = db.Column(db.BigInteger(), primary_key=True)
    nickname = db.Column(db.String(20), nullable=True, index=True)
    avatar = db.Column(db.String(), nullable=True)
    avatar_medium = db.Column(db.String(), nullable=True)
    avatar_full = db.Column(db.String(), nullable=True)

    verified = db.Column(db.Boolean(), nullable=False, default=False, server_default='False')
    ban_date = db.Column(db.DateTime, nullable=True, default=None)

    current_match = db.Column(db.Integer, db.ForeignKey('match.id'))
    solo_mmr = db.Column(db.Integer(), nullable=True)
    section = db.Column(db.String, nullable=True)

    scoreboards = db.relationship('Scoreboard', lazy='dynamic', back_populates='user')
    user_permission = db.relationship('UserPermission', secondary=permissions, lazy='dynamic',
                                      backref=db.backref('users', lazy='dynamic'))
    user_mix_detail = db.relationship("UserMixDetail", uselist=False, backref=db.backref('user', uselist=False))
    profile_scan_info = db.relationship("ProfileScanInfo", uselist=False, backref=db.backref('user', uselist=False))
    matches = db.relationship('PlayerInMatch', back_populates='player')

    def __init__(self, steam_id):
        """Instantiate a new user with default values.

        Args:
            steam_id: Unique user identifier in Steam (as 64 bits).
        """
        self.id = steam_id
        self.nickname = None
        self.current_match = None
        self.last_scan = None
        self.avatar = None
        self.avatar_medium = None
        self.avatar_full = None
        self.verified = False
        self.solo_mmr = None
        self.ban_date = None

    @staticmethod
    def is_authenticated(self):
        """Indicates if the user is authenticated in the system."""
        return True

    @staticmethod
    def is_active(self):
        """Indicates if the user is disabled or not."""
        return True

    @staticmethod
    def is_anonymous(self):
        """Indicates if the user is anonymous or not."""
        return False

    def get_id(self):
        """Get the unique User ID.

        Returns:
            Unique user ID, which is a Steam ID (as 64 bits).
        """
        return self.id

    def has_permission(self, name):
        """Check if the user has a specific permission.

        Args:
            name: `str` permission to check.
        Returns:
            `Boolean` True iff the user has the target permission.
        """
        for permission in self.user_permission:
            if permission.name == name:
                return True
        return False

    def give_permission(self, name, give):
        """Give or remove a specific permission to this user.

        Args:
            name: `str` permission to change.
            give: `Boolean` to specify a permission addition or removal.
        """
        permission = UserPermission.query.filter_by(name=name).first()
        if permission is None:
            return

        if give and permission not in self.user_permission:
            self.user_permission.append(permission)
        elif not give and permission in self.user_permission:
            self.user_permission.remove(permission)
        db.session.commit()

    @staticmethod
    def get_or_create(steam_id):
        """Helpers to always obtain a User object from a SteamID.

        Args:
            steam_id: User SteamID (as 64 bits).
        Returns:
            The `User` of this unique ID, newly created if necessary.
        """
        user = User.query.filter_by(id=steam_id).one_or_none()
        if user is None:
            user = User(steam_id)
            db.session.add(user)
            db.session.commit()
        return user


class ProfileScanInfo(db.Model):
    """Information about the last profile scan done.

    Attributes:
        id: `User` id this scan info is linked to.
        last_scan_request: last time the user pressed the scan button.
        last_scan: last time a bot scanned the profile.
    """
    __tablename__ = 'profile_scan_info'

    id = db.Column(db.BigInteger(), db.ForeignKey('user.id'), primary_key=True)

    last_scan_request = db.Column(db.DateTime, nullable=False)
    last_scan = db.Column(db.DateTime, nullable=True)

    def __init__(self, user):
        """Create a `ProfileScanInfo` from a user.

        Args:
            user: `User` this information is about.
        """
        self.id = user.id
        self.last_scan_request = datetime(year=2000, month=1, day=1)
        self.last_scan = None


class UserPermission(db.Model):
    """Possible permissions for a user.

    Attributes:
        id: unique permission ID.
        name: permission name (cf constants).
    """
    __tablename__ = 'user_permission'

    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(20))

    def __init__(self, name):
        """Create a new permission.

        A permission should never be created in the application.
        The database of permission is populated from the database migrations.

        Args:
            name: permission name.
        """
        self.name = name


class UserMixDetail(db.Model):
    """A user mix description when a user is looking for teammates.

    Attributes
        id: ID of the `User` looking for mates.
        refresh_date: `Date` the ad was last refreshed.
        enabled: `Boolean` if the user wants the ad visible or not.
        title: `str` title of the ad.
        goal: `str` aim of the ad.
        level: `str` level of the ad.
        description: `str` Markdown description of the ad.
    """
    __tablename__ = 'user_mix_details'

    id = db.Column(db.BigInteger(), db.ForeignKey('user.id'), primary_key=True)

    refresh_date = db.Column(db.DateTime, index=True, nullable=False)
    enabled = db.Column(db.Boolean, nullable=False, default=False)
    title = db.Column(db.String(40), nullable=True)
    goal = db.Column(db.String(40), nullable=True)
    level = db.Column(db.String(20), nullable=True)
    description = db.Column(db.Text, nullable=True)

    def __init__(self):
        """Create an ad to look for players, disabled by default."""
        self.refresh_date = datetime.utcnow()
        self.enabled = False

    def update(self, title, goal, level, description):
        """Update the ad with new information.

        Args:
            title: `str` title of the ad.
            goal: `str` aim of the ad.
            level: `str` level of the ad.
            description: `str` Markdown description of the ad.
        """
        self.refresh_date = datetime.utcnow()
        self.title = title
        self.goal = goal
        self.level = level
        self.description = description

    def toggle(self, enable):
        """Toggle visibility of the ad.

        Args:
            enable: `Boolean` True iff the ad should be displayed.
        """
        self.refresh_date = datetime.utcnow()
        self.enabled = enable


class QueuedPlayer(db.Model):
    """Users currently queued in the different ladders.

    Attributes:
        id: Unique ID of the User queued.
        queue_name: queue label the player is queued in (cf. constants).
        added: `datetime` that refer to when the User entered
        mode_vote: modes chosen by the player
        selection_vote: selection chosen by the player.
    """
    __tablename__ = 'queued_player'

    id = db.Column(db.BigInteger(), db.ForeignKey('user.id'), primary_key=True)
    queue_name = db.Column(db.String(20), primary_key=True)
    mode_vote = db.Column(db.Integer, nullable=False, default=0, server_default='0')
    selection_vote = db.Column(db.Integer, nullable=False, default=0, server_default='0')

    added = db.Column(db.DateTime, index=True, nullable=False)

    def __init__(self, id, queue_name):
        """Create a new User in Queue.

        Args:
            id: Unique ID of the User to queue.
            queue_name: Name of the queue to add the User into.
        """
        self.id = id
        self.queue_name = queue_name
        self.added = datetime.utcnow()
        self.mode_vote = 0
        self.selection_vote = 0


class PlayerInMatch(db.Model):
    """Association of users inside matches, with additional information.

    Attributes:
        player_id: Foreign User id.
        match_id: Foreign Match id.
        mmr_before: MMR of the User before the match.
        mmr_after: MMR of the User after the match.
        is_radiant: `Boolean` True iff the player is Radiant.
        team_slot: `int` position of the player in the team, from 1 to 5.
        is_leaver: `Boolean` True iff the player left the match in progress.
        is_dodge: `Boolean` True iff the player did not join the match.
        player: ORM relationship to the `User` this player is linked to.
        match: ORM relationship to the `Match` played.
    """

    player_id = db.Column(db.BigInteger(), db.ForeignKey('user.id'), primary_key=True)
    match_id = db.Column(db.Integer, db.ForeignKey('match.id'), primary_key=True)

    mmr_before = db.Column(db.Integer, nullable=False)
    mmr_after = db.Column(db.Integer, nullable=True)
    is_radiant = db.Column(db.Boolean, nullable=False)
    team_slot = db.Column(db.Integer, nullable=False)
    is_leaver = db.Column(db.Boolean, nullable=False)
    is_dodge = db.Column(db.Boolean, nullable=False, default='false', server_default='false')

    player = db.relationship('User', back_populates='matches')
    match = db.relationship('Match', back_populates='players')

    def __init__(self, player, match, is_radiant, team_slot):
        """Create a new player of the match.

        Args:
            player: `User` this player is linked to.
            match: `Match` this player is linked to.
            is_radiant: `Boolean` True iff the player is Radiant.
            team_slot: `int` the slot the player in the team, from 1 to 5.
        """
        self.player_id = player.user_id
        self.match = match
        self.mmr_before = player.mmr
        self.mmr_after = None
        self.is_radiant = is_radiant
        self.team_slot = team_slot

        self.is_leaver = False
        self.is_dodge = False


class Match(db.Model):
    """A match played in the application

    Attributes:
        id: unique match identifier.
        status: current status of the match (cf. constants).
        created: `datetime` of the match creation (in the database).
        password: password of the Dota lobby.
        server: IP of the Dota server the match is played on, for spectating.
        section: ladder of the match (cf. constants).
        radiant_win; `Boolean` True/False iff Radiant/Dire wins, None otherwise.
        players: ORM relationship to the `PlayerInMatch` of this `Match`
    """
    __tablename__ = 'match'

    id = db.Column(db.Integer, primary_key=True)
    status = db.Column(db.Integer, index=True, nullable=False)
    created = db.Column(db.DateTime, index=True, nullable=False)
    password = db.Column(db.String(20), nullable=False)
    server = db.Column(db.String, nullable=True)
    section = db.Column(db.String, nullable=False, default=constants.LADDER_HIGH, server_default=constants.LADDER_HIGH)
    radiant_win = db.Column(db.Boolean, nullable=True, default=None)

    players = db.relationship('PlayerInMatch', back_populates='match')

    def __init__(self, players, section):
        """Create a new match object.

        Args:
            players: `array` of `User` playing in this `Match`.
            section: ladder name this match is played on (cf. constants).
        """
        self.section = section
        self.radiant_win = None
        self.created = datetime.now()
        self.status = constants.MATCH_STATUS_CREATION
        self.password = 'dz_'
        self.server = None
        for i in range(0, 4):
            self.password += random.choice(string.ascii_lowercase + string.digits)
        is_radiant = True
        sums = {True: 0, False: 0}
        count = {True: 0, False: 0}
        for player in Scoreboard.query.filter(Scoreboard.user_id.in_(players),
                                              Scoreboard.ladder_name == self.section).order_by(
                Scoreboard.mmr.desc()).all():
            if sums[is_radiant] > sums[not is_radiant] and count[not is_radiant] < 5:
                is_radiant = not is_radiant
            sums[is_radiant] += player.mmr
            count[is_radiant] += 1
            player_in_match = PlayerInMatch(player, self, is_radiant, count[is_radiant])
            self.players.append(player_in_match)


class Scoreboard(db.Model):
    """Stats of users in the different ladders.

    Attributes:
        user_id: Unique `User` identifier.
        ladder_name: ladder name this scoreboard is about (cf. constants).
        mmr: `int` MMR of the user in the ladder
        matches: `int` number of matches played, win + loss + leave.
        win: `int` number of wins.
        loss: `int` number of losses.
        dodge: `int` number of dodges before game start.
        leave: `int` number of leaves mid-game.
        user: ORM relationship to the `User` this scoreboard is about.
    """
    __tablename__ = 'scoreboard'

    user_id = db.Column(db.BigInteger(), db.ForeignKey('user.id'), primary_key=True)
    ladder_name = db.Column(db.String, primary_key=True)

    mmr = db.Column(db.Integer, nullable=False, index=True)
    matches = db.Column(db.Integer, nullable=False, default=0, server_default='0')
    win = db.Column(db.Integer, nullable=False, default=0, server_default='0')
    loss = db.Column(db.Integer, nullable=False, default=0, server_default='0')
    dodge = db.Column(db.Integer, nullable=False, default=0, server_default='0')
    leave = db.Column(db.Integer, nullable=False, default=0, server_default='0')

    user = db.relationship('User', back_populates='scoreboards')

    def __init__(self, user, ladder_name):
        """Create a new scoreboard for a user in a ladder.

        Args:
            user: `User` of this `Scoreboard`
            ladder_name: `str` name of the ladder (cf. constants).
        """
        self.user = user
        self.ladder_name = ladder_name

        self.mmr = 5000
        self.win = 0
        self.loss = 0
        self.dodge = 0
        self.leave = 0
        self.matches = 0
