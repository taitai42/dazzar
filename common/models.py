
from datetime import datetime
import string
import random

from flask_sqlalchemy import SQLAlchemy

import common.constants as constants

db = SQLAlchemy()


permissions = db.Table('permissions',
                       db.Column('permission_id', db.Integer, db.ForeignKey('user_permission.id')),
                       db.Column('user_id', db.String(40), db.ForeignKey('user.id')))


class User(db.Model):
    """A user representation in the database.

    Attributes:
        id - unique id, steam ID
        nickname - unique nickname of the user, None at the first logging
        permissions - permissions of the current user
    Methods:
        has_permission - test if user has a specific permission
        give_permission - give a specific permission to the user
        get_or_create - return user of given steam id, create it if necessary
    """
    __tablename__ = 'user'

    id = db.Column(db.String(40), primary_key=True)
    nickname = db.Column(db.String(20), nullable=True, index=True)
    permissions = db.relationship('UserPermission', secondary=permissions,
                                  lazy='dynamic', backref=db.backref('users', lazy='dynamic'))

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
        if not permission or not permission in self.permissions:
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
        rv = User.query.filter_by(id=steam_id).first()
        if rv is None:
            rv = User()
            rv.id = steam_id
            db.session.add(rv)
            db.session.commit()
        return rv


class UserPermission(db.Model):
    """A possible permission for a user.

    Attributes:
        id - unique permission ID
        name - name of the permission (cf constants)
    """
    __tablename__ = 'user_permission'

    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(20))


class QueueVIP(db.Model):
    """Users currently queued for a game.

    Attributes:
        id - user steam id
        added - timestamp of user queue event
    """
    __tablename__ = 'queue_vip'

    id = db.Column(db.String(40), db.ForeignKey('user.id'), primary_key=True)
    added = db.Column(db.DateTime, index=True, nullable=False)

    def __init__(self, id):
        self.id = id
        self.added = datetime.now()


players = db.Table('players',
    db.Column('user_id', db.String(40), db.ForeignKey('user.id')),
    db.Column('match_vip_id', db.Integer, db.ForeignKey('match_vip.id'))
)


class MatchVIP(db.Model):
    """Table of all the matches in the league.

    Attributes:
        id - unique match ID
        created - timestamp of the match creation event
        status - current status of the match, of type MatchStatus
        password - password of the Dota lobby
    """

    __tablename__= 'match_vip'

    id = db.Column(db.Integer, primary_key=True)
    created = db.Column(db.DateTime, index=True, nullable=False)
    status = db.Column(db.Integer, nullable=False)
    password = db.Column(db.String(20), nullable=False)
    players = db.relationship('User', secondary=players, backref=db.backref('matches', lazy='dynamic'))

    def __init__(self, players):
        self.created = datetime.now()
        self.status = constants.MATCH_STATUS_CREATION
        self.password = 'dz_'
        for i in range(0,4):
            self.password += random.choice(string.ascii_lowercase + string.digits)
