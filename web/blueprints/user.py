from flask import Blueprint, current_app, request, url_for, abort, redirect, render_template, jsonify
from flask_login import current_user

from common.models import db, User, UserPermission
from common.helpers import validate_nickname
import common.constants as constants


def make_blueprint():

    user_blueprint = Blueprint('user_blueprint', __name__)

    @user_blueprint.route('/nickname', methods=['GET', 'POST'])
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

    @user_blueprint.route('/nickname/delete/<string:steam_id>')
    def nickname_delete(steam_id):
        """Delete user nickname if admin.
        Force user to chose a new one.

        Parameters:
            steam_id - user concerned
        """
        target_user = User.query.filter_by(id=steam_id).first()
        if target_user is not None \
            and current_user.is_authenticated \
            and current_user.has_permission(constants.PERMISSION_ADMIN):
            target_user.nickname = None
            db.session().commit()
        return redirect(url_for('user_blueprint.user', steam_id=steam_id))

    @user_blueprint.route('/users')
    def users():
        """Page to list all users of the website"""
        return render_template('users.html')

    @user_blueprint.route('/api/users')
    def api_users():
        """Endpoint for the datatable to request users."""

        draw = request.args.get('draw', '1')
        search = request.args.get('search[value]', '')
        length = 50
        start = int(request.args.get('start', '0'))

        query = User.query\
            .order_by(User.nickname)\
            .filter(User.nickname.isnot(None))

        if search != '':
            query = query.filter(User.nickname.like('%' + search + '%'))

        count = query.count()

        query = query.offset(start)\
            .limit(length)

        data = []
        for user in query.all():
            permissions = ""
            permissions += "A " if user.has_permission(constants.PERMISSION_ADMIN) else "- "
            permissions += "V " if user.has_permission(constants.PERMISSION_VOUCH_VIP) else "- "
            permissions += "J " if user.has_permission(constants.PERMISSION_PLAY_VIP) else "- "
            data.append([user.id, user.nickname, permissions])
        results = {
            "draw": draw,
            "recordsTotal": count,
            "recordsFiltered": count,
            "data": data
        }
        return jsonify(results)

    @user_blueprint.route('/user/<string:steam_id>')
    def user(steam_id):
        """Page to list all users of the website.

        Parameters
            steam_id - user to return the detailed page of
        """
        user_requested = User.query.filter_by(id=steam_id).first()
        if user_requested is None:
            abort(404)
        else:
            return render_template('user.html', user=user_requested)

    @user_blueprint.route('/permission/<string:steam_id>/<string:permission>/<string:give>')
    def user_permission(steam_id, permission, give):
        """Modify user permission according to parameters.

        Parameters
            steam_id - user to modify
            permission - right to change
            give - boolean to decide to add permission or remove
        """
        give = give == 'True'
        target_user = User.query.filter_by(id=steam_id).first()
        if target_user is None:
            return redirect(url_for('user_blueprint.user', steam_id=steam_id))

        if current_user.is_authenticated and ((permission == constants.PERMISSION_ADMIN and current_user.has_permission(constants.PERMISSION_ADMIN))
                                              or (permission == constants.PERMISSION_VOUCH_VIP and current_user.has_permission(constants.PERMISSION_ADMIN))
                                              or (permission == constants.PERMISSION_PLAY_VIP and current_user.has_permission(constants.PERMISSION_VOUCH_VIP))):
            target_user.give_permission(permission, give)
            db.session().commit()
        return redirect(url_for('user_blueprint.user', steam_id=steam_id))

    return user_blueprint
