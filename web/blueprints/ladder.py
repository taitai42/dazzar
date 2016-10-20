import re, logging

from flask import Blueprint, current_app, request, url_for, abort, redirect, render_template, jsonify
from flask_login import current_user, login_required


def make_blueprint():
    ladder_blueprint = Blueprint('ladder_blueprint', __name__)

    @ladder_blueprint.route('/ladder/play')
    @login_required
    def ladder_play():
        """Page to enter the league queue."""
        return render_template('ladder_play.html')

    @ladder_blueprint.route('/ladder/scoreboard')
    def ladder_scoreboard():
        """Displays the league scoreboard."""
        return render_template('ladder_scoreboard.html')

    return ladder_blueprint
