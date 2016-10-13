from enum import IntEnum
from datetime import datetime
import string
import random

from flask_sqlalchemy import SQLAlchemy

db = SQLAlchemy()


class UserBasicRights(IntEnum):
    Default = 0
    Banned = 1
    AdminRights = 2
    PlayVIP = 4
    VouchVIP = 8


class User(db.Model):
    __tablename__ = 'users'

    id = db.Column(db.String(40), primary_key=True)
    nickname = db.Column(db.String(20), nullable=True, index=True)
    basic_rights = db.Column(db.Integer, nullable=False, default=0)

    def is_authenticated(self):
        return True

    def is_active(self):
        return True

    def is_anonymous(self):
        return False

    def get_id(self):
        return self.id

    def has_right(self, right):
        return (right | self.basic_rights) > 0

    def give_rights(self, right):
        self.basic_rights = self.basic_rights & right

    @staticmethod
    def get_or_create(steam_id):
        rv = User.query.filter_by(id=steam_id).first()
        if rv is None:
            rv = User()
            rv.id = steam_id
            db.session.add(rv)
            db.session.commit()
        return rv


class QueueVIP(db.Model):
    __tablename__ = 'queue_vip'

    id = db.Column(db.Integer, db.ForeignKey('users.id'), primary_key=True)
    added = db.Column(db.DateTime, index=True, nullable=False)

    def __init__(self, id):
        self.id = id
        self.added = datetime.now()


class MatchStatus(IntEnum):
    Creation = 0
    InProgress = 1
    Cancelled = 2
    Over = 3


class MatchVIP(db.Model):
    __tablename__= 'match_vip'

    id = db.Column(db.Integer, primary_key=True)
    created = db.Column(db.DateTime, index=True, nullable=False)
    status = db.Column(db.Integer, nullable=False)
    password = db.Column(db.String(20), nullable=False)

    def __init__(self):
        self.created = datetime.now()
        self.status = MatchStatus.Creation
        self.password = 'dz_'
        for i in range[0:3]:
            self.password += random.choice(string.ascii_lowercase + string.digits)
