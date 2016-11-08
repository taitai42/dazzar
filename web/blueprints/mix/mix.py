from flask import Blueprint, request, url_for, redirect, render_template


def make_blueprint():

    mix_blueprint = Blueprint('mix_blueprint', __name__, template_folder='templates')

    @mix_blueprint.route('/mix/users')
    def mix_users():
        return render_template('mix_users.html')

    return mix_blueprint
