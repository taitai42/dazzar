import pika
from threading import Thread
from enum import IntEnum


class QueueAdapter:
    """Adapter to interact with the dazzar job queue.

    Attributes
        connection - pika connection to rabbitmq
        channel - job queue to produce/consume

        consume_thread
    """

    def __init__(self):
        self.connection = pika.BlockingConnection(pika.ConnectionParameters(host='dazzar_rabbitmq'))
        self.channel = self.connection.channel()
        self.channel.basic_qos(prefetch_count=1)
        self.channel.queue_declare(queue='dazzar_jobs', durable=True)
        self.consume_thread = None

    def produce(self, message):
        self.channel.basic_publish(exchange='',
                                   routing_key='dazzar_jobs',
                                   body=message,
                                   properties=pika.BasicProperties(
                                       delivery_mode=2,  # make message persistent
                                   ))

    def consume(self, consumer):
        self.channel.basic_consume(consumer, queue='dazzar_jobs')
        self.channel.start_consuming()

    def consume_forever(self, consumer):
        self.consume_thread = Thread(target=self.consume, args=[consumer])
        self.consume_thread.start()


class JobType(IntEnum):
    """Possible job types to process by steam bots.
    """
    ScanProfile = 0
    CreateGame = 1


class Job:
    """The job class.

    Attributes
        type - The job type from JobType enum
        steam_id - steam_id of a user if necessary
        game_id - game_id of a game if necessary
    """
    def __init__(self, job_type=JobType.ScanProfile, steam_id=0, game_id=0):
        self.type = job_type
        self.steam_id = steam_id
        self.game_id = game_id
