import logging
import pickle
from datetime import datetime, timedelta

from flask import Blueprint, request, current_app, url_for, abort, redirect, render_template, jsonify
from flask_login import current_user, login_required

from common.models import db, User, ProfileScanInfo, Scoreboard
from common.job_queue import QueueAdapter, Job, JobType
from common.helpers import validate_nickname
import common.constants as constants


def make_blueprint(job_queue):
    user_blueprint = Blueprint('user_blueprint', __name__, template_folder='templates')

    @user_blueprint.route('/nickname', methods=['GET', 'POST'])
    @login_required
    def nickname():
        """User nickname creation page.

        Methods:
            GET - give the page if nickname not setup
            POST - setup the nickname if valid
        """
        if current_user.nickname is not None:
            return redirect(url_for('index'))

        if request.method == 'GET':
            return render_template('user_nickname.html')
        elif request.method == 'POST':
            posted_nickname = request.form.get('nickname')

            error = validate_nickname(posted_nickname)
            if error is not None:
                return render_template('user_nickname.html', error=error)

            if db.session().query(User).filter_by(nickname=posted_nickname).first() is not None:
                return render_template('user_nickname.html', error='Le pseudo est déjà utilisé.')
            current_user.nickname = posted_nickname
            db.session().commit()
            return redirect(url_for('index'))
        abort(404)

    @user_blueprint.route('/nickname/delete/<int:steam_id>')
    @login_required
    def nickname_delete(steam_id):
        """Delete user nickname if admin.
        Force user to chose a new one.

        Parameters:
            steam_id - user concerned
        """
        steam_id = int(steam_id)
        target_user = db.session().query(User).filter_by(id=steam_id).first()
        if target_user is not None and current_user.has_permission(constants.PERMISSION_ADMIN):
            target_user.nickname = None
            target_user.verified = False
            target_user.section = None
            db.session().commit()
        return redirect(url_for('user_blueprint.user', steam_id=steam_id))

    @user_blueprint.route('/user/force_out/<int:steam_id>')
    @login_required
    def force_out(steam_id):
        """
        """
        steam_id = int(steam_id)
        target_user = db.session().query(User).filter_by(id=steam_id).first()
        if target_user is not None and current_user.has_permission(constants.PERMISSION_ADMIN):
            target_user.current_match = None
            db.session().commit()
        return redirect(url_for('user_blueprint.user', steam_id=steam_id))

    @user_blueprint.route('/user/verify/<int:steam_id>')
    @login_required
    def verify_user(steam_id):
        """Verify or Unverify an user

        Parameters:
            steam_id - user concerned
        """
        steam_id = int(steam_id)
        target_user = db.session().query(User).filter_by(id=steam_id).first()
        if target_user is not None and current_user.has_permission(constants.PERMISSION_ADMIN):
            target_user.verified = not target_user.verified
            db.session().commit()
        return redirect(url_for('user_blueprint.user', steam_id=steam_id))

    @user_blueprint.route('/users')
    def users():
        """Page to list all users of the website"""
        return render_template('user_list.html')

    @user_blueprint.route('/api/users')
    def api_users():
        """Endpoint for the datatable to request users."""

        draw = request.args.get('draw', '1')
        search = request.args.get('search[value]', '')
        length = int(request.args.get('length', '20'))
        start = int(request.args.get('start', '0'))

        query = db.session().query(User) \
            .order_by(User.nickname) \
            .filter(User.nickname.isnot(None))

        if search != '':
            query = query.filter(User.nickname.ilike('%' + search + '%'))

        count = query.count()

        query = query.offset(start) \
            .limit(length)

        data = []
        for user in query.all():
            permissions = {
                'verified': user.verified,
                constants.PERMISSION_ADMIN: user.has_permission(constants.PERMISSION_ADMIN)
            }
            data.append([user.avatar, permissions, user.nickname, str(user.id), user.solo_mmr, user.section])
        results = {
            "draw": draw,
            "recordsTotal": count,
            "recordsFiltered": count,
            "data": data
        }
        return jsonify(results)

    @user_blueprint.route('/user/<int:steam_id>')
    def user(steam_id):
        """Page to give details of a user.

        Parameters
            steam_id - user to return the detailed page of
        """
        user_requested = db.session().query(User).filter_by(id=steam_id).first()
        if user_requested is None:
            abort(404)
        if current_user.is_authenticated and current_user.id == user_requested.id and \
                (current_user.profile_scan_info is None or
                             datetime.utcnow() - current_user.profile_scan_info.last_scan_request > timedelta(
                         minutes=5)):
            scan_possible = True
        else:
            scan_possible = False
        return render_template('user_details.html', user=user_requested, scan_possible=scan_possible)

    @user_blueprint.route('/user/profile')
    @login_required
    def user_profile():
        if (current_user.profile_scan_info is None or
                        datetime.utcnow() - current_user.profile_scan_info.last_scan_request > timedelta(minutes=5)):
            scan_possible = True
        else:
            scan_possible = False
        return render_template('user_details.html', user=current_user, scan_possible=scan_possible)

    @user_blueprint.route('/permission/<int:steam_id>/<string:permission>/<string:give>')
    @login_required
    def user_permission(steam_id, permission, give):
        """Modify user permission according to parameters.

        Parameters
            steam_id - user to modify
            permission - right to change
            give - boolean to decide to add permission or remove
        """
        give = give == 'True'
        target_user = db.session().query(User).filter_by(id=steam_id).first()
        if target_user is None:
            return redirect(url_for('user_blueprint.user', steam_id=steam_id))

        if current_user.has_permission(constants.PERMISSION_ADMIN):
            target_user.give_permission(permission, give)
            if permission == constants.PERMISSION_PLAY_VIP and give and target_user.vip_mmr is None:
                target_user.vip_mmr = 2000
            db.session().commit()
        return redirect(url_for('user_blueprint.user', steam_id=steam_id))

    @user_blueprint.route('/user/scan')
    @login_required
    def user_scan():
        """Queue a job to check the solo MMR of the selected user.
        """
        if current_user.profile_scan_info is None:
            current_user.profile_scan_info = ProfileScanInfo(current_user)
        elif datetime.utcnow() - current_user.profile_scan_info.last_scan_request < timedelta(minutes=5):
            return redirect(url_for('user_blueprint.user', steam_id=current_user.id))

        current_user.profile_scan_info.last_scan_request = datetime.utcnow()
        db.session.commit()

        job_queue.produce(pickle.dumps(Job(JobType.ScanProfile, steam_id=current_user.id)))

        return redirect(url_for('user_blueprint.user', steam_id=current_user.id))

    @user_blueprint.route('/user/section/<int:steam_id>/<string:ladder>')
    @login_required
    def user_section(steam_id, ladder):
        target_user = db.session().query(User).filter_by(id=steam_id).first()
        if target_user is not None and\
            ladder in [constants.LADDER_HIGH, constants.LADDER_MEDIUM, constants.LADDER_LOW] and\
                current_user.has_permission(constants.PERMISSION_ADMIN):
            target_user.section = ladder
            scoreboard = Scoreboard.query.filter_by(user_id=target_user.id, ladder_name=ladder).first()
            if scoreboard is None:
                scoreboard = Scoreboard(target_user, ladder)
                db.session.add(scoreboard)
            db.session().commit()
        return redirect(url_for('user_blueprint.user', steam_id=steam_id))

    return user_blueprint
