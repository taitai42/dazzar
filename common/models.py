from flask_sqlalchemy import SQLAlchemy

db = SQLAlchemy()


class User(db.Model):
    __tablename__ = 'users'

    id = db.Column(db.String(40), primary_key=True)
    nickname = db.Column(db.String(80), nullable=True, index=True)

    def is_authenticated(self):
        return True

    def is_active(self):
        return True

    def is_anonymous(self):
        return False

    def get_id(self):
        return self.id

    @staticmethod
    def get_or_create(steam_id):
        rv = User.query.filter_by(id=steam_id).first()
        if rv is None:
            rv = User()
            rv.id = steam_id
            db.session.add(rv)
            db.session.commit()
        return rv
