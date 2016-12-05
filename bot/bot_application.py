import logging
import pickle
import random
from gevent import Greenlet, sleep

from bot.dota_bot import DotaBot
from web.web_application import create_app
from common.job_queue import QueueAdapter

# Log
logging.basicConfig(format='[%(asctime)s] %(levelname)s %(message)s', level=logging.INFO)


class Credential:
    """A Steam account credentials.

    Attributes:
        login: Steam user login.
        password: Steam user password.
    """

    def __init__(self, login, password):
        """Create a user credentials.

        Args:
            login: user login.
            password: user password.
        """
        self.login = login
        self.password = password


class DazzarWorkerManager(Greenlet):
    """Master class starting Dota bots to process jobs.

    The manager contains a initial pool of Steam Credentials.
    It is a thread listening to the job queue, starting new Dota bots when a new job is available.
    After a job process, the Dota bot informs that the credentials are available again.

    Attributes:
        app: The flask application the manager is linked to, containing configuration objects and database access.
        working_bots: A dictionary of all currently working Dota bots, indexed by bot login.
    """

    def __init__(self):
        """Initialize the worker manager thread.

        Fetch credentials from config and connects to the job queue.
        """
        Greenlet.__init__(self)

        # Initialize
        self.app = create_app()
        self.working_bots = {}
        self.credentials = []
        self.queue = QueueAdapter(self.app.config['RABBITMQ_LOGIN'], self.app.config['RABBITMQ_PASSWORD'])

        # Parse credentials from config
        for i in range(0, self.app.config['STEAM_CREDENTIAL_COUNT']):
            login = self.app.config['STEAM_BOT{0}_LOGIN'.format(i)]
            password = self.app.config['STEAM_BOT{0}_PASSWORD'.format(i)]
            self.credentials.append(Credential(login, password))

    def _run(self):
        """Start the main loop of the thread, creating Dota bots to process available jobs."""
        while True:
            self.queue.refresh()  # Ensure that the queue connection is not closed.

            if len(self.credentials) != 0:
                job = self.queue.consume()
                if job is not None:
                    # Process the job with a new Dota bot
                    credential = self.credentials.pop(random.randint(0, len(self.credentials) - 1))
                    g = DotaBot(worker_manager=self, credential=credential, job=job)
                    g.start()
                    self.working_bots[credential.login] = g

                    self.queue.ack_last()
            sleep(1)

    def bot_end(self, credential):
        """Signal that a bot has finished it work and the credential is free to use again.

        Args:
            credential: `Credential` of the bot.
        """
        self.working_bots.pop(credential.login)
        self.credentials.append(credential)


# Start a Manager if this file is the main script.
if __name__ == '__main__':
    g = DazzarWorkerManager()
    g.start()
    g.join()
