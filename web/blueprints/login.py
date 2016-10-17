import re

from flask import Blueprint, current_app, request, url_for, redirect, render_template
from flask_login import LoginManager, current_user, login_user, login_required, logout_user
from flask_openid import OpenID

from common.models import User


def make_blueprint(oid, login_manager):

    login_blueprint = Blueprint('login_blueprint', __name__)

    @login_manager.user_loader
    def load_user(user_id):
        """Load User before every request."""
        user = User.query.filter_by(id=user_id).first()
        return user

    @login_blueprint.route('/login')
    def login():
        """Login page that invite to login with steam."""
        return render_template('login.html')

    @login_blueprint.route('/logout')
    @login_required
    def logout():
        """Logout the current user and switch back to index."""
        logout_user()
        return redirect(url_for('index'))

    @login_blueprint.before_request
    def nickname_checker():
        """Function that test user nickname before each request.
        If not define, it redirects to the setup page.
        """
        if request.endpoint == 'nickname' or request.endpoint == 'logout':
            return None

        if current_user.is_authenticated and (current_user.nickname is None):
            return redirect(url_for('user_blueprint.nickname'))
        return None

    @login_blueprint.route('/login/steam')
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

    return login_blueprint
