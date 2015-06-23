# -*- coding: utf-8 -*-
import logging
import sys

import spa
import pika
import utc
from werkzeug.exceptions import HTTPException

from mettle.web.exceptions import classpath, EXCEPTION_JSON_RESPONSES

logger = logging.getLogger(__name__)
logger.setLevel(logging.INFO)


class ApiView(spa.Handler):
    def __init__(self, *args, **kwargs):
        super(ApiView, self).__init__(*args, **kwargs)
        self.db = self.app.db # convenience

    def on_rabbit_message(self, ch, method, props, body):
        self.ws.send(body)

    def bind_queue_to_websocket(self, exchange, routing_keys):
        settings = self.app.settings
        self.rabbit_conn = pika.BlockingConnection(pika.URLParameters(settings.rabbit_url))
        channel = self.rabbit_conn.channel()

        queue = channel.queue_declare(exclusive=True)
        queue_name = queue.method.queue

        logger.debug('Rabbit socket on %s/%s' % (exchange, routing_keys))
        channel.exchange_declare(exchange=exchange, type='topic', durable=True)

        for rk in routing_keys:
            channel.queue_bind(exchange=exchange,
                               queue=queue_name,
                               routing_key=rk)

        channel.basic_consume(self.on_rabbit_message, no_ack=True, queue=queue_name)

        last_ping = utc.now()
        while True:
            now = utc.now()
            elapsed = (now - last_ping).total_seconds()
            if elapsed > settings.websocket_ping_interval:
                self.ws.send_frame('', self.ws.OPCODE_PING)
                last_ping = now
            self.rabbit_conn.process_data_events()

    def websocket_close(self):
        self.db.close()
        rabbit_conn = getattr(self, 'rabbit_conn', None)
        if rabbit_conn:
            rabbit_conn.close()

    def __call__(self, environ, start_response):
        try:
            return super(ApiView, self).__call__(environ, start_response)
        except Exception as e:
            if isinstance(e, HTTPException):
                # The framework can deal with these.
                raise
            logger.debug(str(e))
            # For other kinds of exceptions, fall back to our mapping.
            cls_path = classpath(e)
            resp_cls = EXCEPTION_JSON_RESPONSES[cls_path]
            if self.app.settings.show_tracebacks:
                _, _, traceback = sys.exc_info()
            else:
                traceback = None

            return resp_cls(str(e), traceback=traceback)(environ, start_response)
