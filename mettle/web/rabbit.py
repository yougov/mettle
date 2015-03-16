import logging

import pika

logging.basicConfig()
logger = logging.getLogger(__name__)
logger.setLevel(logging.INFO)


def state_message_stream(rabbit_url, exchange, routing_key):
    connection = pika.BlockingConnection(pika.URLParameters(rabbit_url))
    channel = connection.channel()

    queue = channel.queue_declare(exclusive=True)
    queue_name = queue.method.queue

    logger.info('Rabbit socket on %s/%s' % (exchange, routing_key))
    channel.exchange_declare(exchange=exchange, type='topic', durable=True)
    channel.queue_bind(exchange=exchange,
                       queue=queue_name,
                       routing_key=routing_key)
    for method, properties, body in channel.consume(queue=queue_name,
                                                    no_ack=True):
        yield body


