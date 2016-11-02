import logging
from time import sleep

from bot.dota_bot import DotaBotThread

# Log
logging.basicConfig(format='[%(asctime)s] %(levelname)s (%(threadName)-8s) %(name)s: %(message)s', level=logging.INFO)


class DazzarWorkerManager:
    """Master class for the worker part.
    The manager is responsible of the different Dota bots.
    """

    def __init__(self):
        # Init thread pool
        self.bots = []
        self.bots.append(DotaBotThread())

    def start(self):
        """Entry point of the manager.

        :return:
        """
        for bot in self.bots:
            bot.start()

        # Pool sanity check TODO
        while True:
            sleep(30)

# Start if main script
if __name__ == '__main__':
    DazzarWorkerManager().start()
