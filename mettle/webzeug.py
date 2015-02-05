# -*- coding: utf-8 -*-
from werkzeug.routing import Map, Rule
from werkzeug.wrappers import BaseRequest, BaseResponse
from werkzeug.exceptions import HTTPException, MethodNotAllowed, \
     NotImplemented, NotFound


class Request(BaseRequest):
    """Encapsulates a request."""


class Response(BaseResponse):
    """Encapsulates a response."""


class View(object):
    """Baseclass for our views."""

    def __init__(self, app, req):
        self.app = app
        self.req = req

    def GET(self):
        raise MethodNotAllowed()
    POST = DELETE = PUT = GET

    def HEAD(self):
        return self.GET()


class App(object):
    def __init__(self, urls):
        self.urls = urls
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
            view = view_cls(self, req)
            if req.method not in ('GET', 'HEAD', 'POST',
                                  'DELETE', 'PUT'):
                raise NotImplemented()
            resp = getattr(view, req.method)(**params)
        except HTTPException, e:
            resp = e
        return resp(environ, start_response)

