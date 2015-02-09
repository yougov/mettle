from mettle.web.green import patch; patch()

import os
from gevent import pywsgi
from geventwebsocket.handler import WebSocketHandler
from geventwebsocket.gunicorn.workers import GeventWebSocketWorker

from mettle.web.framework import App
from mettle.web import views
from mettle.settings import get_settings


routes = [
    ('/', 'index', views.Index),
    ('/people/<name>/', 'hello', views.Hello),
    ('/count/', 'count', views.Counter),
    ('/socketcount/', 'socketcount', views.SocketCounter),
    ('/messages/', 'messages', views.StreamMessages),
    ('/echo/', 'echo', views.SocketEcho),
]

app = App(routes, get_settings())

if __name__ == "__main__":
    server = pywsgi.WSGIServer(('', int(os.getenv('PORT', 8000))), app,
                               handler_class=WebSocketHandler)
    server.serve_forever()
