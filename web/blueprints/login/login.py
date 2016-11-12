import re
import logging
from steam import WebAPI


from flask import current_app, Blueprint, request, url_for, redirect, render_template
from flask_login import current_user, login_user, login_required, logout_user

from common.models import db, User


def make_blueprint(oid, login_manager):
    login_blueprint = Blueprint('login_blueprint', __name__, template_folder='templates')

    @login_manager.user_loader
    def load_user(user_id):
        """Load User before every request."""
        user = User.query.filter_by(id=user_id).first()
        return user

    @login_blueprint.route('/login')
    def login():
        """Login page that invite to login with steam."""
        return render_template('login_login.html')

    @login_blueprint.route('/logout')
    @login_required
    def logout():
        """Logout the current user and switch back to index."""
        logout_user()
        return redirect(url_for('index'))

    @login_blueprint.before_app_request
    def nickname_checker():
        """Function that test user nickname before each request.
        If not define, it redirects to the setup page.
        """
        if not current_user.is_authenticated or current_user.nickname is not None:
            return None
        if request.endpoint in ['user_blueprint.nickname',
                                'login_blueprint.logout',
                                'static']:
            return None
        return redirect(url_for('user_blueprint.nickname'))

    @login_blueprint.route('/login/steam')
    @oid.loginhandler
    def login_steam():
        """Steam openid caller."""
        if current_user.is_authenticated:
            return redirect(url_for('index'))
        return oid.try_login('http://steamcommunity.com/openid')

    # Regex to get steam id from openid url
    _steam_id_re = re.compile('steamcommunity.com/openid/id/(.*?)$')
    # Steam API access

    @oid.after_login
    def create_or_login(resp):
        """Function called after steam login."""
        match = _steam_id_re.search(resp.identity_url)
        steam_id = int(match.group(1))

        user = User.get_or_create(steam_id)

        api = WebAPI(key=current_app.config['STEAM_KEY'])
        resp=api.ISteamUser.GetPlayerSummaries_v2(steamids=steam_id)
        user.avatar = resp['response']['players'][0]['avatar']
        user.avatar_medium = resp['response']['players'][0]['avatarmedium']
        user.avatar_full = resp['response']['players'][0]['avatarfull']
        db.session.commit()

        logging.error('%s', user.avatar)

        login_user(user)
        return redirect(url_for('index'))

    return login_blueprint
