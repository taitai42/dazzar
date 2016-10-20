#####################
# Application Setup #
#####################

import re

from flask import Flask, abort, jsonify, request, render_template, url_for, session, json, g, redirect, abort
from flask_migrate import Migrate
from flask_login import LoginManager, current_user, login_user, logout_user, login_required
from flask_openid import OpenID

from common.models import db, User
from common.configuration import load_config


app = Flask(__name__)
load_config(app)
db.init_app(app)
migrate = Migrate(app, db)

oid = OpenID(app, store_factory=lambda: None)
login_manager = LoginManager()
login_manager.init_app(app)
login_manager.login_view = 'login_blueprint.login'

#######################
# Blueprints Register #
#######################


import web.blueprints.login as login_blueprint
import web.blueprints.user as user_blueprint
import web.blueprints.ladder as ladder_blueprint


app.register_blueprint(login_blueprint.make_blueprint(oid, login_manager))
app.register_blueprint(user_blueprint.make_blueprint())
app.register_blueprint(ladder_blueprint.make_blueprint())

##########
# Routes #
##########


@app.route('/')
def index():
    """Main page with rules and more..."""
    return render_template('index.html')


############################
# Start Tornado Web Server #
############################


if __name__ == "__main__":
    from tornado.wsgi import WSGIContainer
    from tornado.httpserver import HTTPServer
    from tornado.ioloop import IOLoop

    http_server = HTTPServer(WSGIContainer(app))
    http_server.listen(8000)
    IOLoop.instance().start()
