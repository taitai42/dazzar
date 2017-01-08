import logging
import pickle
from datetime import datetime, timedelta

from flask import Blueprint, request, current_app, url_for, abort, redirect, render_template, jsonify
from flask_login import current_user, login_required

from common.models import db, User, ProfileScanInfo, Scoreboard
from common.job_queue import JobScan
from common.helpers import validate_nickname
import common.constants as constants


def make_blueprint(job_queue):
    """Factory to create the Blueprint responsible for the user features.

    Args:
        job_queue: `QueueAdapter` to send jobs to the Dota bots.
    Returns:
        `Blueprint` handling user features.
    """
    user_blueprint = Blueprint('user_blueprint', __name__, template_folder='templates')

    @user_blueprint.route('/nickname', methods=['GET'])
    @login_required
    def nickname():
        """User nickname page.

        Returns:
            The page to modify the nickname.
        """
        if current_user.nickname is not None:
            return redirect(url_for('index'))

        return render_template('user_nickname.html')

    @user_blueprint.route('/api/nickname/select', methods=['POST'])
    @login_required
    def select_nickname():
        if current_user.nickname is not None:
            return jsonify({
                'status': 'ko',
                'message': "L'utilisateur a déjà un nickname."}), 200

        data = request.get_json(silent=False, force=True)
        posted_nickname = data['nickname']

        error = validate_nickname(posted_nickname)
        if error is not None:
            return jsonify({
                'status': 'ko',
                'message': error}), 200

        if db.session().query(User).filter_by(nickname=posted_nickname).first() is not None:
            return jsonify({
                'status': 'ko',
                'message': 'Le pseudo est déjà utilisé.'}), 200
        current_user.nickname = posted_nickname
        db.session().commit()

        return jsonify({'status': 'ok'}), 200

    @user_blueprint.route('/ban', methods=['GET'])
    @login_required
    def ban():
        """User ban description page.

        Returns:
            Show the ban page if user is banned.
        """
        if current_user.ban_date is None or current_user.ban_date < datetime.utcnow():
            return redirect(url_for('index'))
        return render_template('user_ban.html')

    @user_blueprint.route('/user/ban/<int:steam_id>/<int:time>', methods=['GET'])
    @login_required
    def user_ban(steam_id, time):
        """Ban a user for some time.

        Args:
            steam_id: user targeted.
            time: time to add to the ban.
        """
        target_user = User.query.filter_by(id=steam_id).first()
        if target_user is not None and current_user.has_permission(constants.PERMISSION_ADMIN):
            if target_user.ban_date is None or target_user.ban_date < datetime.utcnow():
                target_user.ban_date = datetime.utcnow()
            maximum_timedelta = datetime.max - target_user.ban_date - timedelta(days=1)
            if maximum_timedelta < timedelta(minutes=time):
                target_user.ban_date += maximum_timedelta
            else:
                target_user.ban_date += timedelta(minutes=time)
            db.session.commit()
        return redirect(url_for('user_blueprint.user', steam_id=steam_id))

    @user_blueprint.route('/user/unban/<int:steam_id>', methods=['GET'])
    @login_required
    def user_unban(steam_id):
        """Unban the target user.

        Args:
            steam_id: user targeted.
        """
        target_user = User.query.filter_by(id=steam_id).first()
        if target_user is not None and current_user.has_permission(constants.PERMISSION_ADMIN):
            target_user.ban_date = None
            db.session.commit()
        return redirect(url_for('user_blueprint.user', steam_id=steam_id))

    @user_blueprint.route('/nickname/delete/<int:steam_id>')
    @login_required
    def nickname_delete(steam_id):
        """Tool for an admin to delete a user nickname. Force to choose a new one.

        Args:
            steam_id: user targeted.
        Returns:
            The user detail page.
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
        """Admin tool to force a player out of a specific match.

        Args:
            steam_id: user targeted.
        Returns:
            The user detail page.
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
        """Verify or un-verify an user

        Args:
            steam_id: user targeted.
        Returns:
            The user detail page.
        """
        steam_id = int(steam_id)
        target_user = db.session().query(User).filter_by(id=steam_id).first()
        if target_user is not None and current_user.has_permission(constants.PERMISSION_ADMIN):
            target_user.verified = not target_user.verified
            db.session().commit()
        return redirect(url_for('user_blueprint.user', steam_id=steam_id))

    @user_blueprint.route('/users')
    def users():
        """Access the page to list all (valid) users of the website.

        Returns:
            The page to list all users of the website.
        """
        return render_template('user_list.html')

    @user_blueprint.route('/api/users')
    def api_users():
        """API endpoint for the datatable to request users.

        Parameters:
            draw: request identifier, returned in the answer.
            length: entries to return.
            start: offset for the entry.
        Returns:
            `JSON` containing user entries sorted with the following design
             {
                "draw": <draw parameter>
                "recordsTotal": <total entries>
                "recordsFiltered": <total entries>
                "data": [ entry.data ]
            }
        """
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
        """Access to the page with details of a user.

        Args:
            steam_id: user ID to return the detailed page of.
        Returns:
            Page with the detailed information of the user.
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
        user_banned = user_requested.ban_date is not None and user_requested.ban_date > datetime.utcnow()
        return render_template('user_details.html', user=user_requested, scan_possible=scan_possible, user_banned=user_banned)

    @user_blueprint.route('/user/profile')
    @login_required
    def user_profile():
        """Access to the page with details of the current user.
.
        Returns:
            Page with the detailed information of the current user.
        """
        if (current_user.profile_scan_info is None or
                        datetime.utcnow() - current_user.profile_scan_info.last_scan_request > timedelta(minutes=5)):
            scan_possible = True
        else:
            scan_possible = False
        return render_template('user_details.html', user=current_user, scan_possible=scan_possible)

    @user_blueprint.route('/permission/<int:steam_id>/<string:permission>/<string:give>')
    @login_required
    def user_permission(steam_id, permission, give):
        """Modify user permission of a specific user.

        Args:
            steam_id: user ID of the `User` to modify.
            permission: `str` permission to change.
            give: `Boolean` to specify a permission addition or removal.
        """
        give = give == 'True'
        target_user = db.session().query(User).filter_by(id=steam_id).first()
        if target_user is None:
            return redirect(url_for('user_blueprint.user', steam_id=steam_id))

        if current_user.has_permission(constants.PERMISSION_ADMIN):
            target_user.give_permission(permission, give)
            db.session().commit()
        return redirect(url_for('user_blueprint.user', steam_id=steam_id))

    @user_blueprint.route('/user/scan/<int:user_id>')
    @login_required
    def user_scan(user_id):
        """Queue a job to check the solo MMR of the selected user.

        Args:
            user_id: user ID of the `User` to scan.
        Returns:
            Redirection to the user detail page.
        """
        if current_user.id == user_id or current_user.has_permission(constants.PERMISSION_ADMIN):
            target_user = User.query.filter_by(id=user_id).first()
            if target_user is not None:
                if target_user.profile_scan_info is None:
                    target_user.profile_scan_info = ProfileScanInfo(target_user)

                if current_user.has_permission(constants.PERMISSION_ADMIN) or \
                   datetime.utcnow() - target_user.profile_scan_info.last_scan_request > timedelta(minutes=5):

                    target_user.profile_scan_info.last_scan_request = datetime.utcnow()
                    db.session.commit()
                    job_queue.produce(JobScan(steam_id=target_user.id))

        return redirect(url_for('user_blueprint.user', steam_id=user_id))

    @user_blueprint.route('/user/section/<int:steam_id>/<string:ladder>')
    @login_required
    def user_section(steam_id, ladder):
        """Change the ladder the user is playing into.

        Args:
            steam_id: user ID of the `User` to change the ladder.
            ladder: `str` ladder_name to put the user into (cf. constants).
        Returns:
            Redirection to the user detail page.
        """
        target_user = db.session().query(User).filter_by(id=steam_id).first()
        if target_user is not None and \
                        ladder in [constants.LADDER_HIGH, constants.LADDER_MEDIUM, constants.LADDER_LOW] and \
                current_user.has_permission(constants.PERMISSION_ADMIN):
            target_user.section = ladder
            scoreboard = Scoreboard.query.filter_by(user_id=target_user.id, ladder_name=ladder).first()
            if scoreboard is None:
                scoreboard = Scoreboard(target_user, ladder)
                db.session.add(scoreboard)
            db.session().commit()
        return redirect(url_for('user_blueprint.user', steam_id=steam_id))

    return user_blueprint
