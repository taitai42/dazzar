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


def load_config(config):
    """Load a configuration for the Flask application.
    Starts with config object as a base
    Loads settings.cfg if exists and readable.

    Attributes:
        app - Application to load into
    """
    config.from_object('common.configuration.Config')
    if isfile(os.path.join(os.path.dirname(__file__), 'settings.cfg')):
        try:
            config.from_pyfile(os.path.join(os.path.dirname(__file__), 'settings.cfg'))
        except SyntaxError:
            logging.log(logging.ERROR, 'Impossible to interpret settings file, using default.')
