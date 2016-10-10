from flask import Flask, abort, jsonify, request, render_template, url_for
from flask_migrate import Migrate

from common.models import db
from common.configuration import load_config

app = Flask(__name__)
load_config(app)
db.init_app(app)
migrate = Migrate(app, db)


@app.route('/', methods=['GET', 'POST'])
def index():
    return 'Hello World'


if __name__ == "__main__":
    from tornado.wsgi import WSGIContainer
    from tornado.httpserver import HTTPServer
    from tornado.ioloop import IOLoop

    http_server = HTTPServer(WSGIContainer(app))
    http_server.listen(8000)
    IOLoop.instance().start()
