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
    permissions = db.relationship('UserPermission', secondary=permissions, lazy='dynamic',
                                  backref=db.backref('users', lazy='dynamic'))

    current_match = db.Column(db.Integer, db.ForeignKey('match.id'), nullable=True)

    last_scan = db.Column(db.DateTime, nullable=True)
    solo_mmr = db.Column(db.Integer(), nullable=True)

    def __init__(self, steam_id):
        self.id = steam_id
        self.nickname = None
        self.current_match = None
        self.last_scan = None
        self.solo_mmr = None

    def is_authenticated(self):
        return True

    def is_active(self):
        return True

    def is_anonymous(self):
        return False

    def get_id(self):
        return self.id

    def has_permission(self, name):
        permission = UserPermission.query.filter_by(name=name).first()
        if not permission or permission not in self.permissions:
            return False
        return True

    def give_permission(self, name, give):
        permission = UserPermission.query.filter_by(name=name).first()
        if permission is None:
            return

        if give and permission not in self.permissions:
            self.permissions.append(permission)
        elif not give and permission in self.permissions:
            self.permissions.remove(permission)

    @staticmethod
    def get_or_create(steam_id):
        user = User.query.filter_by(id=steam_id).first()
        if user is None:
            user = User(steam_id)
            db.session.add(user)
            db.session.commit()
        return user


class UserPermission(db.Model):
    """A possible permission for a user.

    Attributes:
        id - unique permission ID
        name - name of the permission (cf constants)
    """
    __tablename__ = 'user_permission'

    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(20))


class QueuedPlayer(db.Model):
    """Users currently queued for a game.

    Attributes:
        id - user steam id
        queue_name - queue label the player is queued, cf constants
        added - timestamp of user queue event
    """
    __tablename__ = 'queued_player'

    id = db.Column(db.BigInteger(), db.ForeignKey('user.id'), primary_key=True)
    queue_name = db.Column(db.String(20), nullable=False)
    added = db.Column(db.DateTime, index=True, nullable=False)

    def __init__(self, id, queue_name):
        self.id = id
        self.queue_name = queue_name
        self.added = datetime.now()


class Match(db.Model):
    """Table of all the matches in the league.

    Attributes:
        id - unique match ID
        created - timestamp of the match creation event
        status - current status of the match, cf constants
        password - password of the Dota lobby
    """
    __tablename__= 'match'

    id = db.Column(db.Integer, primary_key=True)
    status = db.Column(db.Integer, index=True, nullable=False)
    created = db.Column(db.DateTime, index=True, nullable=False)
    password = db.Column(db.String(20), nullable=False)
    players = db.relationship('User', lazy='joined')

    def __init__(self, players):
        self.created = datetime.now()
        self.status = constants.MATCH_STATUS_CREATION
        self.password = 'dz_'
        for i in range(0,4):
            self.password += random.choice(string.ascii_lowercase + string.digits)
        for player in User.query.filter(User.id.in_(players)).all():
            self.players.append(player)
