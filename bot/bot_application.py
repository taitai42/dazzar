import logging
from time import sleep
import pika

from bot.dota_bot import DotaBotThread
import common.constants as constants

# Log
logging.basicConfig(format='[%(asctime)s] %(levelname)s (%(threadName)-8s) %(name)s: %(message)s', level=logging.INFO)


class DazzarWorkerManager:
    """Master class for the woker part.
    The manager is responsible of the different Dota bots.
    """

    def __init__(self):
        # Initialize thread pool
        self.bot1 = DotaBotThread()
        self.bot1.start()

    def start(self):
        """Entry point of the manager.

        :return:
        """
        # Pool sanity check TODO
        while True:
            sleep(30)

# Start if main script
if __name__ == '__main__':
    DazzarWorkerManager().start()
