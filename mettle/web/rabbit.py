import json
import logging

import pika

from mettle.web.framework import View

logging.basicConfig()
logger = logging.getLogger(__name__)
logger.setLevel(logging.INFO)


class RabbitSocketView(View):
    """
    Subclass this view and call its "stream" method to connect to specified
    RabbitMQ exchanges/routing keys, and stream all resulting messages over
    websocket to the client.

    The "bindings" arguments should be a list of two-item tuples, where the
    first item is an exchange name and the second is a routing key, like this:

    [
        ('exchange1', 'routing.key.1'),
        ('exchange2', 'some.other.routing.key'),
    ]

    The queue will be exclusive to this websocket connection, and automatically
    cleaned up on disconnect.

    This view assumes that all payloads in the RabbitMQ messages will be
    parseable as JSON.
    """
    def stream(self, bindings):
        # Make a rabbit connection, bound to all the exchanges.  Exclusive and
        # nameless.
        settings = self.app.settings
        connection = pika.BlockingConnection(pika.URLParameters(settings.rabbit_url))
        channel = connection.channel()

        queue = channel.queue_declare(exclusive=True)
        queue_name = queue.method.queue

        for exchange, routing_key in bindings:
            logger.info('Rabbit socket on %s/%s' % (exchange, routing_key))
            channel.exchange_declare(exchange=exchange, type='topic', durable=True)
            channel.queue_bind(exchange=exchange,
                               queue=queue_name,
                               routing_key=routing_key)

        # Iterate over responses.  stream out json with exchange, routing key,
        # and body bits.

        for method, properties, body in channel.consume(queue=queue_name,
                                                        no_ack=True):
            parsed = json.loads(body)
            msg = json.dumps({
                'exchange': method.exchange,
                'routing_key': method.routing_key,
                'body': parsed
            })
            self.ws.send(msg)
