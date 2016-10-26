import logging
from time import sleep
import pika

from bot.dota_bot import DotaBotThread
import common.constants as constants

# Log
logging.basicConfig(format='[%(asctime)s] %(levelname)s (%(threadName)-8s) %(name)s: %(message)s', level=logging.DEBUG)

# Initialize thread pool
bot1 = DotaBotThread()
bot1.start()


def callback(ch, method, properties, body):
    print(" [x] Received %r" % body)

connection = pika.BlockingConnection(pika.URLParameters('amqp://guest:guest@dazzar_rabbitmq:5672//'))
channel = connection.channel()
channel.queue_declare(queue='dazzar_jobs')
channel.basic_consume(callback,
                      queue='hello',
                      no_ack=True)
channel.start_consuming()

# Thread sanity checks
while True:
    sleep(30)
