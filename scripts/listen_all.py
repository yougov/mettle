#!/usr/bin/env python
"""
This script demonstrates how to take the callback-based interface for the Pika
RabbitMQ driver and wrap it in a syncronous, generator-based interface.  It
works by having the Pika callback put all messages on a FIFO queue, and then
blocks on that queue and yields for each message received.
"""

import sys
import urllib
from getpass import getpass
from pprint import pprint
import json
from datetime import datetime
from Queue import Queue, Empty
from threading import Thread
import logging

import mettle_protocol as mp

import pika

def main():
    logging.basicConfig(
        format='%(asctime)s %(levelname)s %(message)s',
        level=logging.INFO,
    )

    host = '127.0.0.1'
    vhost = '/'
    exchanges = [
        'mettle_state',
        #mp.ANNOUNCE_SERVICE_EXCHANGE,
        #mp.ANNOUNCE_PIPELINE_RUN_EXCHANGE,
        #mp.ACK_PIPELINE_RUN_EXCHANGE,
        #mp.CLAIM_JOB_EXCHANGE,
        #mp.END_JOB_EXCHANGE,
        #mp.JOB_LOGS_EXCHANGE,
    ]

    username = password = 'guest'

    rabbit_url ='amqp://%(username)s:%(password)s@%(host)s:5672/%(vserver)s' % {
        'username': username,
        'password': password,
        'host': host,
        'vserver': urllib.quote(vhost, safe='')}

    connection = pika.BlockingConnection(pika.URLParameters(rabbit_url))
    channel = connection.channel()

    mp.declare_exchanges(channel)

    queue = channel.queue_declare(exclusive=True)
    queue_name = queue.method.queue

    routing_key = '#'

    for exchange in exchanges:
        channel.queue_bind(exchange=exchange,
                           queue=queue_name,
                           routing_key=routing_key)

    for method, properties, body in channel.consume(queue=queue_name):
        payload = json.loads(body)
        print "NEW MESSAGE"
        print "exchange:", method.exchange
        print "routing key:", method.routing_key
        print "headers:", json.dumps(properties.headers, indent=2)
        print "payload:", json.dumps(payload, indent=2)
        print ""
        channel.basic_ack(method.delivery_tag)

if __name__ == '__main__':
    main()

