import logging
import re

from flask import Flask, abort, jsonify, request, render_template, url_for, session, json, g, redirect
from flask_migrate import Migrate
from flask_login import LoginManager, current_user, login_user, logout_user, login_required
from flask_openid import OpenID

from common.models import db, User
from common.configuration import load_config

app = Flask(__name__)
load_config(app)
db.init_app(app)
migrate = Migrate(app, db)

# Login Setup


oid = OpenID(app)
login_manager = LoginManager()
login_manager.init_app(app)
login_manager.login_view = 'login'


@login_manager.user_loader
def load_user(user_id):
    user = User.query.filter_by(id=user_id).first()
    return user


# Routes


@app.route('/')
def index():
    return render_template('index.html')


@app.route('/ladder/play')
@login_required
def ladder_play():
    return render_template('ladder_play.html')


@app.route('/ladder/scoreboard')
def ladder_scoreboard():
    return render_template('ladder_scoreboard.html')


@app.route('/login')
def login():
    return render_template('login.html')


@app.route('/login/steam')
@oid.loginhandler
def login_steam():
    if current_user.is_authenticated:
        return redirect(url_for('index'))
    return oid.try_login('http://steamcommunity.com/openid')


_steam_id_re = re.compile('steamcommunity.com/openid/id/(.*?)$')


@oid.after_login
def create_or_login(resp):
    match = _steam_id_re.search(resp.identity_url)
    user = User.get_or_create(match.group(1))
    login_user(user)
    return redirect(url_for('index'))


@app.route('/logout')
@login_required
def logout():
    logout_user()
    return redirect(url_for('index'))


if __name__ == "__main__":
    from tornado.wsgi import WSGIContainer
    from tornado.httpserver import HTTPServer
    from tornado.ioloop import IOLoop

    http_server = HTTPServer(WSGIContainer(app))
    http_server.listen(8000)
    IOLoop.instance().start()
