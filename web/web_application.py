#####################
# Application Setup #
#####################

from flask import Flask, render_template
from flask_login import LoginManager
from flask_migrate import Migrate
from flask_openid import OpenID
from flaskext.markdown import Markdown

from common.cfg.configuration import load_config
from common.job_queue import QueueAdapter
from common.models import db


def create_app():
    app = Flask(__name__)
    load_config(app.config)
    db.init_app(app)
    return app
app = create_app()
migrate = Migrate(app, db)
Markdown(app)
job_queue = QueueAdapter(app.config['RABBITMQ_LOGIN'], app.config['RABBITMQ_PASSWORD'])

oid = OpenID(app, store_factory=lambda: None)
login_manager = LoginManager()
login_manager.init_app(app)
login_manager.login_view = 'login_blueprint.login'

#######################
# Blueprints Register #
#######################


import web.blueprints.login.login as login_blueprint
import web.blueprints.user.user as user_blueprint
import web.blueprints.ladder.ladder as ladder_blueprint
import web.blueprints.mix.mix as mix_blueprint


app.register_blueprint(login_blueprint.make_blueprint(oid, login_manager))
app.register_blueprint(user_blueprint.make_blueprint(job_queue))
app.register_blueprint(ladder_blueprint.make_blueprint(job_queue))
app.register_blueprint(mix_blueprint.make_blueprint())

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

def refresh_rabbitmq(io_loop):
    global job_queue
    job_queue.refresh()

    loop.call_later(60, refresh_rabbitmq, io_loop)

if __name__ == "__main__":
    from tornado.wsgi import WSGIContainer
    from tornado.httpserver import HTTPServer
    from tornado.ioloop import IOLoop

    http_server = HTTPServer(WSGIContainer(app))
    http_server.listen(8000)
    loop = IOLoop.instance()
    refresh_rabbitmq(loop)
    loop.start()
