import re, logging

from flask import Blueprint, current_app, request, url_for, abort, redirect, render_template, jsonify
from flask_login import current_user, login_required

from common.models import db, User, QueueVIP, MatchVIP
import common.constants as constants


def make_blueprint():

    ladder_blueprint = Blueprint('ladder_blueprint', __name__)

    @ladder_blueprint.route('/ladder/play')
    @login_required
    def ladder_play():
        """Page to enter the league queue.
        Display the queue and enter/quit if user can play."""
        in_queue = False
        current_queue = []

        if current_user.is_authenticated() and current_user.has_permission(constants.PERMISSION_PLAY_VIP):
            if QueueVIP.query.filter_by(id=current_user.id).first() is not None:
                in_queue = True
        for user in QueueVIP.query.order_by(QueueVIP.added).limit(10).from_self().join(User).add_columns(User.id, User.nickname).all():
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

    @ladder_blueprint.route('/queue/<string:add>')
    def queue(add):
        """Queue or dequeue current user."""
        add = add == 'True'

        if current_user.is_authenticated and current_user.has_permission(constants.PERMISSION_PLAY_VIP):
            if add:
                if QueueVIP.query.filter_by(id=current_user.id).first() is None:
                    # Add if less than 9 players, create a game otherwise
                    query = QueueVIP.query.order_by(QueueVIP.added).limit(9)
                    if query.count() < 9:
                        new_queue = QueueVIP(current_user.id)
                        db.session().add(new_queue)
                        db.session().commit()
                    else:
                        players = [current_user.id]
                        for player in query.all():
                            players.append(player.id)
                            db.session().delete(player)
                        new_match = MatchVIP(players)
                        db.session().add(new_match)
                        db.session().commit()
                        return redirect(url_for('ladder_blueprint.ladder_play'))
            else:
                remove_queue = QueueVIP.query.filter_by(id=current_user.id).first()
                if remove_queue is not None:
                    db.session().delete(remove_queue)
                    db.session().commit()

        return redirect(url_for('ladder_blueprint.ladder_play'))

    return ladder_blueprint
