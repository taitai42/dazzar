#####################
# Application Setup #
#####################

import re

from flask import Flask, abort, jsonify, request, render_template, url_for, session, json, g, redirect, abort
from flask_migrate import Migrate
from flask_login import LoginManager, current_user, login_user, logout_user, login_required
from flask_openid import OpenID

from common.models import db, User
from common.configuration import load_config
from common.helpers import validate_nickname

app = Flask(__name__)
load_config(app)
db.init_app(app)
migrate = Migrate(app, db)

oid = OpenID(app, store_factory=lambda: None)
login_manager = LoginManager()
login_manager.init_app(app)
login_manager.login_view = 'login'


@login_manager.user_loader
def load_user(user_id):
    """Load User before every request."""
    user = User.query.filter_by(id=user_id).first()
    return user


#######################
# Blueprints Register #
#######################

# TODO

##########
# Routes #
##########


@app.route('/')
def index():
    """Main page with rules and more..."""
    return render_template('index.html')


@app.route('/ladder/play')
@login_required
def ladder_play():
    """Page to enter the league queue."""
    return render_template('ladder_play.html')


@app.route('/ladder/scoreboard')
def ladder_scoreboard():
    """Displays the league scoreboard."""
    return render_template('ladder_scoreboard.html')


@app.route('/login')
def login():
    """Login page that invite to login with steam."""
    return render_template('login.html')


@app.route('/login/steam')
@oid.loginhandler
def login_steam():
    """Steam openid caller."""
    if current_user.is_authenticated:
        return redirect(url_for('index'))
    return oid.try_login('http://steamcommunity.com/openid')

# Regex to get steam id from openid url
_steam_id_re = re.compile('steamcommunity.com/openid/id/(.*?)$')


@oid.after_login
def create_or_login(resp):
    """Function called after steam login."""
    match = _steam_id_re.search(resp.identity_url)
    user = User.get_or_create(match.group(1))
    login_user(user)
    return redirect(url_for('index'))


@app.route('/logout')
@login_required
def logout():
    logout_user()
    return redirect(url_for('index'))


@app.before_request
def nickname_checker():
    """Function that test user nickname before each request.
    If not define, it redirects to the setup page.
    """
    if request.endpoint == 'nickname' or request.endpoint == 'logout':
        return None

    if current_user.is_authenticated and (current_user.nickname is None):
        return redirect(url_for('nickname'))
    return None


@app.route('/nickname', methods=['GET', 'POST'])
def nickname():
    """User nickname creation page.

    Methods:
        GET - give the page if nickname not setup
        POST - setup the nickname if valid
    """
    if (not current_user.is_authenticated) or (current_user.nickname is not None):
        return redirect(url_for('index'))

    if request.method == 'GET':
        return render_template('nickname.html')
    elif request.method == 'POST':
        posted_nickname = request.form.get('nickname')

        error = validate_nickname(posted_nickname)
        if error is not None:
            return render_template('nickname.html', error=error)

        session = db.session()
        if session.query(User).filter_by(nickname=posted_nickname).first() is not None:
            return render_template('nickname.html', error='Le pseudo est déjà utilisé.')
        user = session.query(User).filter_by(id=current_user.id).first()
        user.nickname = posted_nickname
        db.session().commit()
        return redirect(url_for('index'))

    abort(404)


############################
# Start Tornado Web Server #
############################


if __name__ == "__main__":
    from tornado.wsgi import WSGIContainer
    from tornado.httpserver import HTTPServer
    from tornado.ioloop import IOLoop

    http_server = HTTPServer(WSGIContainer(app))
    http_server.listen(8000)
    IOLoop.instance().start()
