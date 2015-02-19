# -*- coding: utf-8 -*-
import json

import gevent
from werkzeug.routing import Map, Rule
from werkzeug.wrappers import BaseRequest, BaseResponse
from werkzeug.exceptions import (HTTPException, MethodNotAllowed,
                                 NotImplemented, NotFound)


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
        self.db = self.app.db # convenience

    def get(self):
        raise MethodNotAllowed()
    post = delete = put = get

    def head(self):
        return self.GET()

    def __call__(self, environ, start_response):
        if self.request.method not in self.allowed_methods:
            raise NotImplemented()

        if self.request.method == 'GET' and 'wsgi.websocket' in environ:
            self.ws = environ['wsgi.websocket']
            self.websocket(**self.params)
        else:
            handler = getattr(self, self.request.method.lower())
            resp = handler(**self.params)
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
