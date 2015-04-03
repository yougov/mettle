# -*- coding: utf-8 -*-
import json
import logging

import gevent
import pika
import utc
from werkzeug.routing import Map, Rule
from werkzeug.wrappers import BaseRequest, BaseResponse
from werkzeug.exceptions import (HTTPException, MethodNotAllowed,
                                 NotImplemented, NotFound)
logger = logging.getLogger(__name__)
logger.setLevel(logging.INFO)


class Request(BaseRequest):
    """Encapsulates a request."""


class Response(BaseResponse):
    """Encapsulates a response."""


class JSONResponse(Response):
    def __init__(self, data, *args, **kwargs):
        kwargs['content_type'] = 'application/json'
        return super(JSONResponse, self).__init__(json.dumps(data), *args, **kwargs)


class View(object):
    """Baseclass for our views."""

    allowed_methods = ('GET', 'HEAD', 'POST', 'DELETE', 'PUT')

    def __init__(self, app, req, params):
        self.app = app
        self.request = req
        self.params = params

    def get(self):
        raise MethodNotAllowed()
    post = delete = put = get

    def head(self):
        return self.GET()

    def cleanup(self):
        pass

    def __call__(self, environ, start_response):
        if self.request.method not in self.allowed_methods:
            raise NotImplemented()

        if self.request.method == 'GET' and 'wsgi.websocket' in environ:
            self.ws = environ['wsgi.websocket']
            self.ws.close_callbacks = [self.cleanup]

            handler = self.websocket
        else:
            handler = getattr(self, self.request.method.lower())

        resp = handler(**self.params)
        return resp(environ, start_response)


class ApiView(View):
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

        logger.info('Rabbit socket on %s/%s' % (exchange, routing_keys))
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

    def cleanup(self):
        self.db.close()
        rabbit_conn = getattr(self, 'rabbit_conn', None)
        if rabbit_conn:
            rabbit_conn.close()


class App(object):
    def __init__(self, urls, settings):
        self.urls = urls
        self.settings = settings
        self.map, self.handlers = build_rules(urls)

    def __call__(self, environ, start_response):
        try:
            req = Request(environ)
            adapter = self.map.bind_to_environ(environ)
            view_name, params = adapter.match()
            view_cls = self.handlers[view_name]
            wsgi_app = view_cls(self, req, params)
        except HTTPException, e:
            wsgi_app = e
        resp = wsgi_app(environ, start_response)

        return resp


def build_rules(rules_tuples):
    """
    Given a list of tuples like this:

    [
        ('/', 'index', views.Index),
        ('/hello/<name>/', 'hello', views.Hello),
    ]

    Return two things:
        1. A Werkzeug Map object.
        2. A dictionary mapping the names of the Werkzeug endpoints to view
        classes.
    """
    handlers = {}
    rules = []
    for pat, name, view in rules_tuples:
        rules.append(Rule(pat, endpoint=name))
        handlers[name] = view
    return Map(rules), handlers


def reverse(rule_map, endpoint, values=None):
    """ Given a rule map, and the name of one of our endpoints, and a dict of
    parameter values, return a URL"""
    adapter = rule_map.bind('')
    return adapter.build(endpoint, values=values)
