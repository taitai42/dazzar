from os.path import isfile
import os
import logging


class Config(object):
    """Basic configuration used by the application.

    Attributes:
        DEBUG: Flask debugging option.
        TESTING: Flask testing option.
        SQLALCHEMY_TRACK_MODIFICATIONS: Flask SQLalchmey track modifications option.
        DATABASE_URI: Url to the database used in Flask.
        RABBITMQ_LOGIN: Login used to connect to the rabbitmq.
        RABBITMQ_PASSWORD: Password used to connect to the rabbitmq.
        STEAM_KEY: Steam Key to interact with Steam API.
        STEAM_CREDENTIAL_COUNT: Number of steam accounts provided into the config.
        STEAM_BOTi_LOGIN: Login of the steam account i.
        STEAM_BOTi_PASSWORD: Password of the steam account i.
        VIP_LADDER_OPEN: Boolean indicating if the ladder is open for queue.
    """

    DEBUG = True
    TESTING = True
    SQLALCHEMY_TRACK_MODIFICATIONS = False
    DATABASE_URI = 'sqlite://:memory:'
    RABBITMQ_LOGIN = 'dazzar'
    RABBITMQ_PASSWORD = 'guest'
    STEAM_KEY = 'toto'
    STEAM_CREDENTIAL_COUNT = 1
    STEAM_BOT0_LOGIN = 'login'
    STEAM_BOT0_PASSWORD = 'password'
    VIP_LADDER_OPEN = False


def load_config(config):
    """Load a configuration for the Flask application from a specific file.

    Starts with `Config` object as a base.
    Loads `settings.cfg` if exists and readable.

    Args:
        config: Application config object to load the config into.
    """
    config.from_object('common.cfg.configuration.Config')
    if isfile(os.path.join(os.path.dirname(__file__), 'settings.cfg')):
        try:
            config.from_pyfile(os.path.join(os.path.dirname(__file__), 'settings.cfg'))
        except SyntaxError:
            logging.log(logging.ERROR, 'Impossible to interpret settings file, using default.')
