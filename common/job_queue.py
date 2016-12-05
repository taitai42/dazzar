import pika
from abc import ABC, abstractmethod


class QueueAdapter:
    """Adapter to interact with the dazzar job queue.

    Attributes:
        connection: pika connection to rabbitmq
        channel: job queue to produce/consume
    """

    def __init__(self, username, password):
        """Create an adapter to interact with the job queue.

        Args:
            username: username of the queue
            password: password of the queue
        """
        self.username = username
        self.password = password
        self.connection = None
        self.channel = None
        self.method = None

        self._connect()

    def _connect(self):
        """Initial connection to the queue manager."""
        self.connection = pika.BlockingConnection(pika.ConnectionParameters(host='dazzar_rabbitmq',
                                                                            credentials=pika.PlainCredentials(self.username,
                                                                                                              self.password)))
        self.channel = self.connection.channel()
        self.channel.basic_qos(prefetch_count=1)
        self.channel.queue_declare(queue='dazzar_jobs', durable=True)

    def produce(self, message):
        """Publish a message to add inside the queue.

        Args;
            message: message to add inside the queue, pickled.
        """
        self.channel.basic_publish(exchange='',
                                   routing_key='dazzar_jobs',
                                   body=message,
                                   properties=pika.BasicProperties(
                                       delivery_mode=2,  # make message persistent
                                   ))

    def consume(self):
        """Non blocking consume of messages from the queue.

        Returns:
            A message non pickled from the queue if there is at least one, None otherwise.
        """
        method_frame, header_frame, body = self.channel.basic_get('dazzar_jobs')
        result = None

        if method_frame:
            self.method = method_frame
            result = body

        return result

    def ack_last(self):
        """Acknowledge the last message consumed by the queue."""
        self.channel.basic_ack(delivery_tag=self.method.delivery_tag)

    def refresh(self):
        """Ping the queue to ensure that the TCP connection is not closed prematurely."""
        self.connection.process_data_events()


class Job(ABC):
    """A abstract job class used to pass orders from the flask application to the Dota workers."""


class JobScan(Job):
    """A scan profile job where the bot requests the Dota profile and update the database with information.

    Attributes:
        steam_id: Steam user id (as 64 bits) to scan.
        scan_finish: Boolean indicating the end of the scan or not.
    """

    def __init__(self, steam_id):
        self.steam_id = steam_id
        self.scan_finish = False


class JobCreateGame(Job):
    """A create game job where the bot creates a lobby for a game.

    Attributes:
        match_id: Id of the match to create from the database.
    """

    def __init__(self, match_id):
        self.match_id = match_id
