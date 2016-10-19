import re, logging

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
            .filter(User.nickname is not None)\
            .order_by(User.nickname)\

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
        """Page to list all users of the website"""
        user_requested = User.query.filter_by(id=steam_id).first()
        if user_requested is None:
            abort(404)
        else:
            return render_template('user.html', user=user_requested)

    return user_blueprint
