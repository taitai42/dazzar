import re
from datetime import datetime

from steam import WebAPI
from flask import current_app, Blueprint, request, url_for, redirect, render_template
from flask_login import current_user, login_user, login_required, logout_user

from common.models import db, User


def make_blueprint(oid, login_manager):
    """Factory to create the Blueprint responsible for the login features.

    Args:
        oid: Flask OpenID module of the application.
        login_manager: Flask LoginManager module of the application.
    Returns:
        `Blueprint` handling login features.
    """
    login_blueprint = Blueprint('login_blueprint', __name__, template_folder='templates')

    @login_manager.user_loader
    def load_user(user_id):
        """Loader of `User` object before every request.

        Args:
            user_id: Unique `User` identifier.
        Returns:
            `User` object of the current user.
        """
        user = User.query.filter_by(id=user_id).first()
        return user

    @login_blueprint.route('/login')
    def login():
        """Login page that invite to login with Steam.

        Returns:
            The login page.
        """
        return render_template('login_login.html')

    @login_blueprint.route('/logout')
    @login_required
    def logout():
        """Logout the current user and switch back to index.

        Returns:
            The index page.
        """
        logout_user()
        return redirect(url_for('index'))

    @login_blueprint.before_app_request
    def user_checker():
        """Check user properties before any request and redirect if necessary.

        Redirects the user to the ban description page if the user is banned.
        Redirects the user to the nickname setting page if not yet created.

        Returns:
            None if the user is not banned, has it nicknames set. HTTP response otherwise.
        """
        if not current_user.is_authenticated:
            return None
        if request.endpoint in ['user_blueprint.nickname',
                                'user_blueprint.select_nickname',
                                'user_blueprint.ban',
                                'login_blueprint.logout',
                                'static']:
            return None

        if current_user.ban_date is not None and current_user.ban_date > datetime.utcnow():
            return redirect(url_for('user_blueprint.ban'))

        if current_user.nickname is not None:
            return None

        return redirect(url_for('user_blueprint.nickname'))

    @login_blueprint.route('/login/steam')
    @oid.loginhandler
    def login_steam():
        """Steam openid caller.

        Returns:
            The index page if already logged, or the OpenID module call result otherwise.
        """
        if current_user.is_authenticated:
            return redirect(url_for('index'))
        return oid.try_login('http://steamcommunity.com/openid')

    # Regex to get steam id from openid url
    _steam_id_re = re.compile('steamcommunity.com/openid/id/(.*?)$')

    @oid.after_login
    def create_or_login(resp):
        """Callback fired after steam login, log user in the application.

        Args:
            resp: OpenID response.
        Returns:
            Index page after login.
        """
        match = _steam_id_re.search(resp.identity_url)
        steam_id = int(match.group(1))

        user = User.get_or_create(steam_id)

        api = WebAPI(key=current_app.config['STEAM_KEY'])
        resp=api.ISteamUser.GetPlayerSummaries_v2(steamids=steam_id)
        user.avatar = resp['response']['players'][0]['avatar']
        user.avatar_medium = resp['response']['players'][0]['avatarmedium']
        user.avatar_full = resp['response']['players'][0]['avatarfull']
        db.session.commit()

        login_user(user, remember=True)
        return redirect(url_for('index'))

    return login_blueprint
