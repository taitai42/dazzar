import pickle

from flask import Blueprint, current_app, request, url_for, redirect, render_template, jsonify
from flask_login import current_user, login_required

from common.helpers import _jinja2_filter_french_date
from common.models import db, User, QueuedPlayer, Match, Scoreboard
from common.job_queue import JobCreateGame
import common.constants as constants


def make_blueprint(job_queue):
    """Factory to create the Blueprint responsible for the ladder features.

    Args:
        job_queue: `QueueAdapter` to send jobs to the Dota bots.
    Returns:
        `Blueprint` handling ladder features.
    """

    ladder_blueprint = Blueprint('ladder_blueprint', __name__, template_folder='templates')

    @ladder_blueprint.route('/ladder/play')
    @login_required
    def ladder_play():
        """Returns the page to enter the league queue.

        Display the queue status and enter/quit if user can play.

        Returns:
            Generated page of the queue status iff the user is not in a game, redirects to the match page otherwise.
        """
        if current_user.current_match is not None:
            return redirect(url_for('ladder_blueprint.match', match_id=current_user.current_match))

        in_queue = False
        current_queues = {constants.LADDER_HIGH: 0, constants.LADDER_LOW: 0, constants.LADDER_MEDIUM: 0}
        is_open = current_app.config['VIP_LADDER_OPEN']

        if is_open:
            if QueuedPlayer.query.filter_by(id=current_user.id).first() is not None:
                in_queue = True

            for key, value in current_queues.items():
                current_queues[key] = QueuedPlayer.query.filter(QueuedPlayer.queue_name == key).limit(10).count()

        return render_template('ladder_play.html', is_open=is_open, current_queues=current_queues, in_queue=in_queue)

    @ladder_blueprint.route('/ladder/open')
    @login_required
    def ladder_open():
        """Open or close the ladders

        Returns:
            Redirect to the page of the queue status.
        """
        if current_user.has_permission('admin'):
            for user in QueuedPlayer.query \
                    .all():
                db.session.delete(user)
            db.session.commit()
            current_app.config['VIP_LADDER_OPEN'] = not current_app.config['VIP_LADDER_OPEN']

        return redirect(url_for('ladder_blueprint.ladder_play'))

    @ladder_blueprint.route('/ladder/scoreboard/<string:ladder>')
    def ladder_scoreboard(ladder):
        """Displays the league scoreboard.

        Returns:
            Page with all the scoreboards.
        """
        return render_template('ladder_scoreboard.html', ladder=ladder)

    @ladder_blueprint.route('/api/scoreboard/<string:ladder>')
    def api_scoreboard(ladder):
        """API endpoint for the datatable to request scoreboards.

        Args:
            ladder: ladder name (cf. constants).
        Parameters:
            draw: request identifier, returned in the answer.
            length: entries to return.
            start: offset for the entry.
        Returns:
            `JSON` containing scoreboard entries sorted with the following design
             {
                "draw": <draw parameter>
                "recordsTotal": <total entries>
                "recordsFiltered": <total entries>
                "data": [ entry.data ]
            }
        """
        draw = request.args.get('draw', '1')
        length = int(request.args.get('length', '20'))
        start = int(request.args.get('start', '0'))
        if ladder not in [constants.LADDER_HIGH, constants.LADDER_LOW, constants.LADDER_MEDIUM]:
            ladder = constants.LADDER_HIGH

        query = db.session().query(User, Scoreboard) \
            .filter(User.id == Scoreboard.user_id) \
            .filter(Scoreboard.ladder_name == ladder) \
            .filter(Scoreboard.matches != 0) \
            .filter(User.nickname.isnot(None)) \
            .order_by(Scoreboard.mmr.desc(), User.solo_mmr.desc())

        count = query.count()

        query = query.offset(start) \
            .limit(length)

        data = []
        place = start
        for user, scoreboard in query.all():
            place += 1
            data.append([user.avatar, place, user.nickname, str(user.id), scoreboard.mmr, user.solo_mmr,
                         scoreboard.matches, scoreboard.win, scoreboard.loss, scoreboard.dodge, scoreboard.leave])
        results = {
            "draw": draw,
            "recordsTotal": count,
            "recordsFiltered": count,
            "data": data
        }
        return jsonify(results)

    @ladder_blueprint.route('/ladder/matches')
    def ladder_matches():
        """Displays the list of all ladder matches.

        Returns:
            Page listing all ladder matches.
        """
        return render_template('ladder_matches.html')

    @ladder_blueprint.route('/api/ladder/matches')
    def api_matches():
        """API endpoint for the datatable to request matches.

        Parameters:
            draw: request identifier, returned in the answer.
            length: entries to return.
            start: offset for the entry.
        Returns:
            `JSON` containing match entries sorted with the following design
             {
                "draw": <draw parameter>
                "recordsTotal": <total entries>
                "recordsFiltered": <total entries>
                "data": [ entry.data ]
            }
        """
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
            data.append([match.id, match.section, match.status, _jinja2_filter_french_date(match.created)])
        results = {
            "draw": draw,
            "recordsTotal": count,
            "recordsFiltered": count,
            "data": data
        }
        return jsonify(results)

    @ladder_blueprint.route('/ladder/match/<int:match_id>')
    def match(match_id):
        """Page to give details of a match.

        Args:
            match_id: match ID to return the detailed page of.
        Returns:
            The page generated with the match details.
        """
        match = db.session().query(Match).filter(Match.id == match_id).first()
        return render_template('ladder_match.html', match=match)

    @ladder_blueprint.route('/queue')
    @login_required
    def queue():
        """Queue or dequeue the current user from it ladder queue.

        Returns:
            Redirection to the queue status.
        """
        if current_user.current_match is None and current_user.section is not None:
            remove_queue = QueuedPlayer.query.filter_by(id=current_user.id).first()
            if remove_queue is not None:
                db.session().delete(remove_queue)
                db.session().commit()
            else:
                new_queue = QueuedPlayer(current_user.id, current_user.section)
                db.session().add(new_queue)
                db.session().commit()

                query = QueuedPlayer.query.filter_by(queue_name=current_user.section) \
                    .order_by(QueuedPlayer.added).limit(10)
                if query.count() >= 10:
                    # Create a game
                    players = []
                    for player in query.all():
                        players.append(player.id)
                        db.session().delete(player)
                    new_match = Match(players, current_user.section)
                    db.session().add(new_match)
                    db.session().commit()
                    for player in new_match.players:
                        player.player.current_match = new_match.id
                    db.session.commit()

                    job_queue.produce(JobCreateGame(match_id=new_match.id))

                    return redirect(url_for('ladder_blueprint.ladder_play'))

        return redirect(url_for('ladder_blueprint.ladder_play'))

    @ladder_blueprint.route('/ladder/match/cancel/<int:match_id>')
    @login_required
    def cancel_match(match_id):
        """Admin tool to cancel a match not already finished or cancelled.

        Args:
            match_id: match ID to cancel.
        Returns:
            Redirection to the match detail page.
        """
        if current_user.has_permission("admin"):
            match_requested = Match.query.filter_by(id=match_id).first_or_404()
            if match_requested.status not in [constants.MATCH_STATUS_CANCELLED, constants.MATCH_STATUS_ENDED]:
                match_requested.status = constants.MATCH_STATUS_CANCELLED
                for player in match_requested.players:
                    player.player.current_match = None
                db.session.commit()
        return redirect(url_for('ladder_blueprint.match', match_id=match_id))

    @ladder_blueprint.route('/ladder/match/outcome/<int:match_id>/<string:outcome>')
    @login_required
    def change_outcome(match_id, outcome):
        """Admin tool to change the outcome of a match finished or cancelled.

        Args:
            match_id: match ID to change the outcome of.
            outcome: 'Radiant' or 'Dire' as the new side winner of the match.
        Returns:
            Redirection to the match detail page.
        """
        if current_user.has_permission("admin"):
            match_requested = Match.query.filter_by(id=match_id).first_or_404()
            if match_requested.status in [constants.MATCH_STATUS_CANCELLED, constants.MATCH_STATUS_ENDED]:
                match_requested.status = constants.MATCH_STATUS_ENDED
                radiant_win = outcome == 'Radiant'
                match_requested.radiant_win = radiant_win
                db.session.commit()

        return redirect(url_for('ladder_blueprint.match', match_id=match_id))

    return ladder_blueprint
