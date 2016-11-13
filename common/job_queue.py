import pika
from pika.exceptions import ConnectionClosed
import logging
from enum import IntEnum


class QueueAdapter():
    """Adapter to interact with the dazzar job queue.

    Attributes
        connection - pika connection to rabbitmq
        channel - job queue to produce/consume

        consume_thread
    """

    def __init__(self, username, password):
        self.username = username
        self.password = password
        self.connection = None
        self.channel = None
        self.consume_thread = None
        self.bot = None
        self.method = None

        self._connect()

    def _connect(self):
        self.connection = pika.BlockingConnection(pika.ConnectionParameters(host='dazzar_rabbitmq',
                                                                            credentials=pika.PlainCredentials(self.username,
                                                                                                              self.password)))
        self.channel = self.connection.channel()
        self.channel.basic_qos(prefetch_count=1)
        self.channel.queue_declare(queue='dazzar_jobs', durable=True)

    def produce(self, message):
        self.channel.basic_publish(exchange='',
                                   routing_key='dazzar_jobs',
                                   body=message,
                                   properties=pika.BasicProperties(
                                       delivery_mode=2,  # make message persistent
                                   ))

    def consume(self):
        method_frame, header_frame, body = self.channel.basic_get('dazzar_jobs')
        result = None

        if method_frame:
            self.method = method_frame
            result = body

        return result

    def ack_last(self):
        self.channel.basic_ack(delivery_tag=self.method.delivery_tag)

    def refresh(self):
        self.connection.process_data_events()


class JobType(IntEnum):
    """Possible job types to process by steam bots.
    """
    ScanProfile = 0
    VIPGame = 1


class Job:
    """The job class.

    Attributes
        type - The job type from JobType enum
        steam_id - steam_id of a user if necessary
        match_id - match_id of a game if necessary
    """
    def __init__(self, job_type=None, steam_id=None, match_id=None):
        self.type = job_type
        self.steam_id = steam_id
        self.match_id = match_id
        self.scan_finish = False
