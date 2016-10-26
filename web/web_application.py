#####################
# Application Setup #
#####################

import pika

from flask import Flask, render_template
from flask_migrate import Migrate
from flask_login import LoginManager
from flask_openid import OpenID

from common.models import db
from common.configuration import load_config


def create_app():
    app = Flask(__name__)
    load_config(app.config)
    db.init_app(app)
    return app
app = create_app()
migrate = Migrate(app, db)


connection = pika.BlockingConnection(pika.URLParameters('amqp://guest:guest@dazzar_rabbitmq:5672//'))
channel = connection.channel()
channel.queue_declare(queue='dazzar_jobs')
channel.basic_publish(exchange='',
                      routing_key='dazzar_jobs',
                      body='Hello World!')

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
