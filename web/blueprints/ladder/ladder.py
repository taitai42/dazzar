import re, logging

from flask import Blueprint, current_app, request, url_for, abort, redirect, render_template, jsonify
from flask_login import current_user, login_required

from common.models import db, User, QueuedPlayer, Match
import common.constants as constants


def make_blueprint():

    ladder_blueprint = Blueprint('ladder_blueprint', __name__, template_folder='templates')

    @ladder_blueprint.route('/ladder/play')
    @login_required
    def ladder_play():
        """Page to enter the league queue.
        Display the queue and enter/quit if user can play."""
        in_queue = False
        current_queue = []

        if current_user.has_permission(constants.PERMISSION_PLAY_VIP):
            if QueuedPlayer.query.filter_by(id=current_user.id, queue_name=constants.QUEUE_NAME_VIP).first() is not None:
                in_queue = True

        for user in QueuedPlayer.query\
                .filter_by(queue_name=constants.QUEUE_NAME_VIP)\
                .order_by(QueuedPlayer.added).limit(10)\
                .from_self().join(User).add_columns(User.id, User.nickname).all():
            current_queue.append(user)

        return render_template('ladder_play.html', current_queue=current_queue, in_queue=in_queue)

    @ladder_blueprint.route('/ladder/scoreboard')
    def ladder_scoreboard():
        """Displays the league scoreboard."""
        return render_template('ladder_scoreboard.html')

    @ladder_blueprint.route('/ladder/matches')
    def ladder_matches():
        """Displays the league matches."""
        return render_template('ladder_matches.html')

    @ladder_blueprint.route('/api/ladder/matches')
    def api_matches():
        """Endpoint for the datatable to request matches."""

        draw = request.args.get('draw', '1')
        length = 20
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
        match_requested = Match.query.filter_by(id=match_id).first_or_404()
        return render_template('ladder_match.html', match=match_requested)

    @ladder_blueprint.route('/queue/<string:add>')
    @login_required
    def queue(add):
        """Queue or dequeue current user."""
        add = add == 'True'

        if current_user.is_authenticated \
                and current_user.has_permission(constants.PERMISSION_PLAY_VIP)\
                and current_user.current_match is None:
            if add:
                if QueuedPlayer.query.filter_by(queue_name=constants.QUEUE_NAME_VIP, id=current_user.id).first() is None:
                    # Add if less than 9 players, create a game otherwise
                    query = QueuedPlayer.query.filter_by(queue_name=constants.QUEUE_NAME_VIP)\
                        .order_by(QueuedPlayer.added).limit(9)
                    if query.count() < 9:
                        new_queue = QueuedPlayer(current_user.id, constants.QUEUE_NAME_VIP)
                        db.session().add(new_queue)
                        db.session().commit()
                    else:
                        players = [current_user.id]
                        for player in query.all():
                            players.append(player.id)
                            db.session().delete(player)
                        new_match = Match(players)
                        db.session().add(new_match)
                        db.session().commit()
                        for user in new_match.players:
                            user.current_game = new_match.id
                        db.session.commit()
                        return redirect(url_for('ladder_blueprint.ladder_play'))
            else:
                remove_queue = QueuedPlayer.query.filter_by(id=current_user.id, queue_name=constants.QUEUE_NAME_VIP).first()
                if remove_queue is not None:
                    db.session().delete(remove_queue)
                    db.session().commit()

        return redirect(url_for('ladder_blueprint.ladder_play'))

    return ladder_blueprint
