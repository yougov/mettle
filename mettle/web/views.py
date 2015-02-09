import time
import json

import pika

from mettle.web.framework import Request, Response, View
import mettle_protocol as mp

class Index(View):
    def get(self):
        return Response('Hello World')


class Hello(View):
    def get(self, name):
        return Response('Hey there ' + name + '!')


class CountIter(object):
    """
    An iterator that increments an integer once per second and yields a
    newline-terminated string
    """
    def __init__(self):
        self.num = 0

    def __iter__(self):
        return self

    def next(self):
        self.num += 1
        time.sleep(1)
        return '%s\n' % self.num


class Counter(View):
    """
    A long-lived stream of incrementing integers, one line per second.

    Best viewed with "curl -n localhost:8000/count/"

    Open up lots of terminals with that command to test how many simultaneous
    connections you can handle.
    """
    def GET(self):
        return Response(CountIter())


class SocketEcho(View):
    def websocket(self, ws):
        message = ws.receive()
        ws.send(message)

class SocketCounter(View):
    def websocket(self, ws):
        for line in CountIter():
            ws.send(line)

class StreamMessages(View):
    def websocket(self, ws):
        # Make a rabbit connection, bound to all the exchanges.  Exclusive and
        # nameless.
        settings = self.app.settings
        connection = pika.BlockingConnection(pika.URLParameters(settings.rabbit_url))
        channel = connection.channel()
        exchanges = [
            mp.ANNOUNCE_PIPELINE_RUN_EXCHANGE,
            mp.ACK_PIPELINE_RUN_EXCHANGE,
            mp.ANNOUNCE_JOB_EXCHANGE,
            mp.ACK_JOB_EXCHANGE,
            mp.END_JOB_EXCHANGE,
            mp.JOB_LOGS_EXCHANGE,
        ]
        # Iterate over responses.  stream out json with exchange, routing key,
        # and body bits.
        queue = channel.queue_declare(exclusive=True)
        queue_name = queue.method.queue

        for exchange in exchanges:
            channel.queue_bind(exchange=exchange,
                               queue=queue_name,
                               routing_key='#')

        for method, properties, body in channel.consume(queue=queue_name,
                                                        no_ack=True):
            parsed = json.loads(body)
            msg = json.dumps({
                'exchange': method.exchange,
                'routing_key': method.routing_key,
                'body': parsed
            })
            ws.send(msg)
