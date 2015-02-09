# -*- coding: utf-8 -*-
import gevent
from werkzeug.routing import Map, Rule
from werkzeug.wrappers import BaseRequest, BaseResponse
from werkzeug.exceptions import (HTTPException, MethodNotAllowed,
                                 NotImplemented, NotFound)


class Request(BaseRequest):
    """Encapsulates a request."""


class Response(BaseResponse):
    """Encapsulates a response."""


class View(object):
    """Baseclass for our views."""

    allowed_methods = ('GET', 'HEAD', 'POST', 'DELETE', 'PUT')

    def __init__(self, app, req, params):
        self.app = app
        self.req = req
        self.params = params

    def get(self):
        raise MethodNotAllowed()
    post = delete = put = get

    def head(self):
        return self.GET()

    def __call__(self, environ, start_response):
        if self.req.method not in self.allowed_methods:
            raise NotImplemented()

        if self.req.method == 'GET' and 'wsgi.websocket' in environ:
            return self.websocket(environ['wsgi.websocket'], **self.params)

        resp = getattr(self, self.req.method.lower())(**self.params)
        return resp(environ, start_response)


class App(object):
    def __init__(self, urls, settings):
        self.urls = urls
        self.settings = settings
        self.handlers = {}
        self.rules = []
        for pat, name, func in urls:
            self.rules.append(Rule(pat, endpoint=name))
            self.handlers[name] = func
        self.map = Map(self.rules)

    def __call__(self, environ, start_response):
        try:
            req = Request(environ)
            adapter = self.map.bind_to_environ(environ)
            view_name, params = adapter.match()
            view_cls = self.handlers[view_name]
            resp = view_cls(self, req, params)
        except HTTPException, e:
            resp = e
        return resp(environ, start_response)


# gevent.pywsgi logging patch adapted from flask-sockets
def log_request(self):
    log = self.server.log
    if log:
        if hasattr(log, 'info'):
            log.info(self.format_request() + '\n')
        else:
            log.write(self.format_request() + '\n')
gevent.pywsgi.WSGIHandler.log_request = log_request
