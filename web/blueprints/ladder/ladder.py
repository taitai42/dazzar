import re
import logging
import pickle

from flask import Blueprint, current_app, request, url_for, abort, redirect, render_template, jsonify
from flask_login import current_user, login_required

from common.models import db, User, QueuedPlayer, Match, PlayerInMatch
from common.job_queue import Job, JobType
import common.constants as constants


def make_blueprint(job_queue):

    ladder_blueprint = Blueprint('ladder_blueprint', __name__, template_folder='templates')

    @ladder_blueprint.route('/ladder/play')
    @login_required
    def ladder_play():
        """Page to enter the league queue.
        Display the queue and enter/quit if user can play."""
        if current_user.current_match is not None:
            return redirect(url_for('ladder_blueprint.match', match_id=current_user.current_match))

        in_queue = False
        current_queue = []
        is_open = current_app.config['VIP_LADDER_OPEN']

        if is_open:
            if current_user.has_permission(constants.PERMISSION_PLAY_VIP):
                if QueuedPlayer.query.filter_by(id=current_user.id, queue_name=constants.QUEUE_NAME_VIP).first() is not None:
                    in_queue = True

            for user, queued_player in db.session().query(User, QueuedPlayer).\
                    filter(User.id == QueuedPlayer.id).\
                    filter(QueuedPlayer.queue_name == constants.QUEUE_NAME_VIP).\
                    order_by(QueuedPlayer.added).limit(10).all():
                current_queue.append(user)

        return render_template('ladder_play.html', is_open=is_open, current_queue=current_queue, in_queue=in_queue)

    @ladder_blueprint.route('/ladder/open')
    @login_required
    def ladder_open():
        """Open or close the ladder."""
        if current_user.has_permission('admin'):
            for user in QueuedPlayer.query\
                    .filter_by(queue_name=constants.QUEUE_NAME_VIP)\
                    .all():
                db.session.delete(user)
            db.session.commit()
            current_app.config['VIP_LADDER_OPEN'] = not current_app.config['VIP_LADDER_OPEN']

        return redirect(url_for('ladder_blueprint.ladder_play'))

    @ladder_blueprint.route('/ladder/scoreboard')
    def ladder_scoreboard():
        """Displays the league scoreboard."""
        return render_template('ladder_scoreboard.html')

    @ladder_blueprint.route('/api/scoreboard')
    def api_scoreboard():
        """Endpoint for the datatable to request user score."""

        draw = request.args.get('draw', '1')
        length = int(request.args.get('length', '20'))
        start = int(request.args.get('start', '0'))

        query = db.session().query(User)\
            .filter(User.nickname.isnot(None))\
            .filter(User.vip_mmr != None)\
            .order_by(User.vip_mmr.desc())

        count = query.count()

        query = query.offset(start)\
            .limit(length)

        data = []
        place = start
        for user in query.all():
            place += 1
            data.append([user.avatar, place, user.nickname, str(user.id), user.vip_mmr, user.solo_mmr])
        results = {
            "draw": draw,
            "recordsTotal": count,
            "recordsFiltered": count,
            "data": data
        }
        return jsonify(results)

    @ladder_blueprint.route('/ladder/matches')
    def ladder_matches():
        """Displays the league matches."""
        return render_template('ladder_matches.html')

    @ladder_blueprint.route('/api/ladder/matches')
    def api_matches():
        """Endpoint for the datatable to request matches."""

        draw = request.args.get('draw', '1')
        length = int(request.args.get('length', '20'))
        start = int(request.args.get('start', '0'))

        query = Match.query \
            .order_by(Match.created.desc())

        count = query.count()

        query = query.offset(start) \
            .limit(length)

        data = []
        for match in query.all():
            data.append([match.id, match.created, match.status])
        results = {
            "draw": draw,
            "recordsTotal": count,
            "recordsFiltered": count,
            "data": data
        }
        return jsonify(results)

    @ladder_blueprint.route('/ladder/match/<int:match_id>')
    def match(match_id):
        """Page to give details of a match

        Parameters
            match_id - match to return the detailed page of
        """
        match = db.session().query(Match).filter(Match.id == match_id).first()
        return render_template('ladder_match.html', match=match)

    @ladder_blueprint.route('/queue')
    @login_required
    def queue():
        """Queue or dequeue current user."""
        if current_user.has_permission(constants.PERMISSION_PLAY_VIP) and current_user.current_match is None:
            remove_queue = QueuedPlayer.query.filter_by(id=current_user.id, queue_name=constants.QUEUE_NAME_VIP).first()
            if remove_queue is not None:
                db.session().delete(remove_queue)
                db.session().commit()
            else:
                new_queue = QueuedPlayer(current_user.id, constants.QUEUE_NAME_VIP)
                db.session().add(new_queue)
                db.session().commit()
                
                query = QueuedPlayer.query.filter_by(queue_name=constants.QUEUE_NAME_VIP)\
                    .order_by(QueuedPlayer.added).limit(10)
                if query.count() >= 10:
                    # Create a game
                    players = []
                    for player in query.all():
                        players.append(player.id)
                        db.session().delete(player)
                    new_match = Match(players)
                    db.session().add(new_match)
                    db.session().commit()
                    for player in new_match.players:
                        player.player.current_match = new_match.id
                    db.session.commit()

                    job_queue.produce(pickle.dumps(Job(JobType.VIPGame, match_id=new_match.id)))

                    return redirect(url_for('ladder_blueprint.ladder_play'))

        return redirect(url_for('ladder_blueprint.ladder_play'))

    @ladder_blueprint.route('/ladder/match/cancel/<int:match_id>')
    @login_required
    def cancel_match(match_id):
        """Page to give details of a match

        Parameters
            match_id - match to return the detailed page of
        """
        if current_user.has_permission("admin"):
            match_requested = Match.query.filter_by(id=match_id).first_or_404()
            if match_requested.status not in [constants.MATCH_STATUS_CANCELLED, constants.MATCH_STATUS_ENDED]:
                match_requested.status = constants.MATCH_STATUS_CANCELLED
                for player in match_requested.players:
                    player.player.current_match = None
                db.session.commit()
        return redirect(url_for('ladder_blueprint.match', match_id=match_id))

    return ladder_blueprint
