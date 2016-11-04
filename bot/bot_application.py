import logging
from time import sleep

from bot.dota_bot import DotaBotThread
from web.web_application import create_app

# Log
logging.basicConfig(format='[%(asctime)s] %(levelname)s %(threadName)s %(message)s', level=logging.INFO)


class DazzarWorkerManager:
    """Master class for the worker part.
    The manager is responsible of the different Dota bots.
    """

    def __init__(self):
        self.app = create_app()

        # Init thread pool
        self.bots = []
        for i in range(0, self.app.config['STEAM_BOT_COUNT']):
            self.bots.append(DotaBotThread(self.app.config['STEAM_BOT{0}_LOGIN'.format(i)],
                                           self.app.config['STEAM_BOT{0}_PASSWORD'.format(i)]))

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
