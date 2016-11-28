import math
from datetime import datetime
import string
import random

from flask_sqlalchemy import SQLAlchemy

import common.constants as constants

db = SQLAlchemy()


permissions = db.Table('permissions',
                       db.Column('permission_id', db.Integer(), db.ForeignKey('user_permission.id')),
                       db.Column('user_id', db.BigInteger(), db.ForeignKey('user.id')))


class User(db.Model):
    """A user representation in the database.

    Attributes:
        id - unique id, steam ID 64 bits
        nickname - unique nickname of the user, None at the first logging
        permissions - permissions of the current user

        current_match - if playing, this is the id of the current match

        last_scan - last time the steam profile was scanned for info
        solo_mmr - player solo mmr found after scan
    Methods:
        has_permission - test if user has a specific permission
        give_permission - give a specific permission to the user
        get_or_create - return user of given steam id, create it if necessary
    """
    __tablename__ = 'user'

    id = db.Column(db.BigInteger(), primary_key=True)
    nickname = db.Column(db.String(20), nullable=True, index=True)
    avatar = db.Column(db.String(), nullable=True)
    avatar_medium = db.Column(db.String(), nullable=True)
    avatar_full = db.Column(db.String(), nullable=True)
    verified = db.Column(db.Boolean(), nullable=False, default=False, server_default='False')

    current_match = db.Column(db.Integer, db.ForeignKey('match.id'))
    solo_mmr = db.Column(db.Integer(), nullable=True)
    section = db.Column(db.String, nullable=True)
    scoreboards = db.relationship('Scoreboard', lazy='dynamic', back_populates='user')

    vip_mmr = db.Column(db.Integer(), nullable=True, index=True)

    user_permission = db.relationship('UserPermission', secondary=permissions, lazy='dynamic', backref=db.backref('users', lazy='dynamic'))
    user_mix_detail = db.relationship("UserMixDetail", uselist=False, backref=db.backref('user', uselist=False))
    profile_scan_info = db.relationship("ProfileScanInfo", uselist=False, backref=db.backref('user', uselist=False))
    matches = db.relationship('PlayerInMatch', back_populates='player')

    def __init__(self, steam_id):
        self.id = steam_id
        self.nickname = None
        self.current_match = None
        self.last_scan = None
        self.avatar = None
        self.avatar_medium = None
        self.avatar_full = None
        self.verified = False

        self.solo_mmr = None
        self.vip_mmr = None

    def is_authenticated(self):
        return True

    def is_active(self):
        return True

    def is_anonymous(self):
        return False

    def get_id(self):
        return self.id

    def has_permission(self, name):
        for permission in self.user_permission:
            if permission.name == name:
                return True
        return False

    def give_permission(self, name, give):
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
        user = User.query.filter_by(id=steam_id).one_or_none()
        if user is None:
            user = User(steam_id)
            db.session.add(user)
            db.session.commit()
        return user


class ProfileScanInfo(db.Model):
    """Informations about the last profile scan done.

    Attributes:
        id - user scan info
        last_scan_request - last time the user pressed the scan button
        last_scan - last time a bot scanned the profile
    """
    __tablename__ = 'profile_scan_info'

    id = db.Column(db.BigInteger(), db.ForeignKey('user.id'), primary_key=True)

    last_scan_request = db.Column(db.DateTime, nullable=False)
    last_scan = db.Column(db.DateTime, nullable=True)

    def __init__(self, user):
        self.id = user.id
        self.last_scan_request = datetime.utcnow()
        self.last_scan = None


class UserPermission(db.Model):
    """A possible permission for a user.

    Attributes:
        id - unique permission ID
        name - name of the permission (cf constants)
    """
    __tablename__ = 'user_permission'

    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(20))

    def __init__(self, name):
        self.name = name


class UserMixDetail(db.Model):
    """A user mix description when a user is looking for mates.

    Attributes
        id - user id of the request
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
        self.refresh_date = datetime.utcnow()
        self.enabled = False

    def update(self, title, goal, level, description):
        self.refresh_date = datetime.utcnow()
        self.title = title
        self.goal = goal
        self.level = level
        self.description = description

    def toggle(self, enable):
        self.refresh_date = datetime.utcnow()
        self.enabled = enable


class QueuedPlayer(db.Model):
    """Users currently queued for a game.

    Attributes:
        id - user steam id
        queue_name - queue label the player is queued, cf constants
        added - timestamp of user queue event
    """
    __tablename__ = 'queued_player'

    id = db.Column(db.BigInteger(), db.ForeignKey('user.id'), primary_key=True)
    queue_name = db.Column(db.String(20), primary_key=True)

    added = db.Column(db.DateTime, index=True, nullable=False)

    def __init__(self, id, queue_name):
        self.id = id
        self.queue_name = queue_name
        self.added = datetime.utcnow()


class PlayerInMatch(db.Model):
    """Association of users inside matches.

    Attributes
        player_id - Foreign user id
        match_id - Foreign match id
        mmr_before - MMR before the encounter
        mmr_after - MMR after the encounter
        is_radiant - Side boolean
        is_leaver - Leaving status of the player
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
        self.player_id = player.user_id
        self.match = match
        self.mmr_before = player.mmr
        self.mmr_after = None
        self.is_radiant = is_radiant
        self.team_slot = team_slot

        self.is_leaver = False
        self.is_dodge = False


class Match(db.Model):
    """Table of all the matches in the league.

    Attributes:
        id - unique match ID
        created - timestamp of the match creation event
        status - current status of the match, cf constants
        password - password of the Dota lobby
        section - ladder target of the match
        radiant_win - T/F if Rad/Dire or None for other reasons
    """
    __tablename__= 'match'

    id = db.Column(db.Integer, primary_key=True)
    status = db.Column(db.Integer, index=True, nullable=False)
    created = db.Column(db.DateTime, index=True, nullable=False)
    password = db.Column(db.String(20), nullable=False)
    server = db.Column(db.String, nullable=True)
    section = db.Column(db.String, nullable=False, default=constants.LADDER_HIGH, server_default=constants.LADDER_HIGH)
    radiant_win = db.Column(db.Boolean, nullable=True, default=None)

    players = db.relationship('PlayerInMatch', back_populates='match')

    def __init__(self, players, section):
        self.section = section
        self.radiant_win = None
        self.created = datetime.now()
        self.status = constants.MATCH_STATUS_CREATION
        self.password = 'dz_'
        self.server = None
        for i in range(0,4):
            self.password += random.choice(string.ascii_lowercase + string.digits)
        is_radiant = True
        sums = {True: 0, False: 0}
        count = {True: 0, False: 0}
        for player in Scoreboard.query.filter(Scoreboard.user_id.in_(players), Scoreboard.ladder_name==self.section).order_by(Scoreboard.mmr.desc()).all():
            if sums[is_radiant] > sums[not is_radiant] and count[not is_radiant] < 5:
                is_radiant = not is_radiant
            sums[is_radiant] += player.mmr
            count[is_radiant] += 1
            player_in_match = PlayerInMatch(player, self, is_radiant, count[is_radiant])
            self.players.append(player_in_match)


class Scoreboard(db.Model):
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
        self.user = user
        self.ladder_name = ladder_name

        self.mmr = 5000
        self.win = 0
        self.loss = 0
        self.dodge = 0
        self.leave = 0
        self.matches = 0
