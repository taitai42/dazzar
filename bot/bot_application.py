import logging
import pickle
import random
from gevent import Greenlet, sleep, spawn, joinall
from eventemitter import EventEmitter

from bot.dota_bot import DotaBot
from web.web_application import create_app
from common.job_queue import QueueAdapter

# Log
logging.basicConfig(format='[%(asctime)s] %(levelname)s %(message)s', level=logging.INFO)


class Credentials:

    def __init__(self, login, password):
        self.login = login
        self.password = password


class DazzarWorkerManager(Greenlet):
    """Master class for the worker part.
    The manager is responsible of the different Dota bots.
    """

    def __init__(self):
        Greenlet.__init__(self)

        self.app = create_app()

        # Parse credentials
        self.credentials = []
        for i in range(0, self.app.config['STEAM_CREDENTIAL_COUNT']):
            login = self.app.config['STEAM_BOT{0}_LOGIN'.format(i)]
            password = self.app.config['STEAM_BOT{0}_PASSWORD'.format(i)]
            self.credentials.append(Credentials(login, password))

        # Workers
        self.working_bots = {}

        # Jobs management
        self.queue = QueueAdapter(self.app.config['RABBITMQ_LOGIN'], self.app.config['RABBITMQ_PASSWORD'])

    def _run(self):
        """Entry point of the manager.
        """
        while True:
            self.queue.refresh()

            if len(self.credentials) != 0:
                message = self.queue.consume()
                if message is not None:
                    job = pickle.loads(message)
                    credential = self.credentials.pop(random.randint(0, len(self.credentials)-1))
                    g = DotaBot(worker_manager=self, credential=credential, job=job)
                    g.start()
                    self.working_bots[credential.login] = g
                    self.queue.ack_last()
            sleep(1)

    def bot_end(self, credential):
        self.working_bots.pop(credential.login)
        self.credentials.append(credential)


# Start if main script
if __name__ == '__main__':
    g = DazzarWorkerManager()
    g.start()
    g.join()

