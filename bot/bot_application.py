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


class DazzarWorkerManager(Greenlet, EventEmitter):
    """Master class for the worker part.
    The manager is responsible of the different Dota bots.
    """

    def __init__(self):
        Greenlet.__init__(self)

        self.app = create_app()
        self.pool_size = self.app.config['STEAM_BOT_COUNT']

        # Parse credentials
        self.credentials = []
        for i in range(0, self.app.config['STEAM_CREDENTIAL_COUNT']):
            login = self.app.config['STEAM_BOT{0}_LOGIN'.format(i)]
            password = self.app.config['STEAM_BOT{0}_PASSWORD'.format(i)]
            self.credentials.append(Credentials(login, password))

        # Init thread pool
        self.starting_bots = {}
        self.available_bots = {}
        self.working_bots = {}

        # Jobs management
        self.queue = QueueAdapter(self.app.config['RABBITMQ_LOGIN'], self.app.config['RABBITMQ_PASSWORD'])

    def _run(self):
        """Entry point of the manager.
        """

        maintainer = spawn(self.worker_pool_maintainer)
        jobs = spawn(self.get_job)

        maintainer.start()
        jobs.start()
        joinall([maintainer, jobs])

    def worker_pool_maintainer(self):
        while True:
            if len(self.credentials) != 0 and len(self.available_bots) < self.pool_size:
                credential = self.credentials.pop(random.randint(0, len(self.credentials)-1))
                self.starting_bots[credential.login] = DotaBot(self, credential)
                self.starting_bots[credential.login].start()
            sleep(20)

    def get_job(self):
        while True:
            self.queue.refresh()

            if len(self.available_bots) != 0:
                message = self.queue.consume()
                if message is not None:
                    job = pickle.loads(message)
                    login, bot = self.available_bots.popitem()
                    self.working_bots[login] = bot
                    bot.emit('new_job', job)
                    self.queue.ack_last()
            sleep(5)

    def bot_started(self, credential):
        g = self.starting_bots.pop(credential.login)
        self.available_bots[credential.login] = g

    def bot_end(self, credential):
        g = self.working_bots.pop(credential.login)
        self.credentials.append(credential)


# Start if main script
if __name__ == '__main__':
    g = DazzarWorkerManager()
    g.start()
    g.join()

