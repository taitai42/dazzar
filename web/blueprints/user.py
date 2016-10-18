import re

from flask import Blueprint, current_app, request, url_for, abort, redirect, render_template
from flask_login import current_user

from common.models import db, User
from common.helpers import validate_nickname


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
        return '{"users": []}'

    return user_blueprint
