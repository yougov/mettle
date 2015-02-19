from mettle.web.green import patch; patch()

import os

from gevent import pywsgi
from geventwebsocket.handler import WebSocketHandler
from geventwebsocket.gunicorn.workers import GeventWebSocketWorker
from werkzeug.wsgi import SharedDataMiddleware
from sqlalchemy.orm import scoped_session

from mettle.web.framework import App
from mettle.web import views
from mettle.settings import get_settings
from mettle.db import make_session_cls


routes = [
    ('/', 'index', views.Index),
    ('/people/<name>/', 'hello', views.Hello),
    ('/count/', 'count', views.Counter),
    ('/socketcount/', 'socketcount', views.SocketCounter),
    ('/messages/', 'messages', views.StreamMessages),
    ('/echo/', 'echo', views.SocketEcho),
    ('/api/services/<service_name>/pipelines/<pipeline_name>/runs/<int:run_id>/logs/',
     'logs_run', views.Log),
    ('/api/services/<service_name>/pipelines/<pipeline_name>/runs/<int:run_id>/targets/<target>/logs/',
     'logs_target', views.Log),
]

if 'app' not in globals():
    settings = get_settings()
    app = App(routes, settings)
    app.db = scoped_session(make_session_cls(settings.db_url))
    app = SharedDataMiddleware(app, {
        '/static': ('mettle', 'static')
    })


if __name__ == "__main__":
    server = pywsgi.WSGIServer(('', int(os.getenv('PORT', 8000))), app,
                               handler_class=WebSocketHandler)
    server.serve_forever()
