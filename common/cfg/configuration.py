from os.path import isfile
import os
import logging


class Config(object):
    """ Basic configuration used by the application.
    It is overriden by settings.cfg file.
    (Only if exists and readable)
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
    """Load a configuration for the Flask application.
    Starts with config object as a base
    Loads settings.cfg if exists and readable.

    Attributes:
        config - Application config object to load into
    """
    config.from_object('common.cfg.configuration.Config')
    if isfile(os.path.join(os.path.dirname(__file__), 'settings.cfg')):
        try:
            config.from_pyfile(os.path.join(os.path.dirname(__file__), 'settings.cfg'))
        except SyntaxError:
            logging.log(logging.ERROR, 'Impossible to interpret settings file, using default.')
