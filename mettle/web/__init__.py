from mettle.web.green import patch; patch()

import os

from gevent import pywsgi
from geventwebsocket.handler import WebSocketHandler
from geventwebsocket.gunicorn.workers import GeventWebSocketWorker
from werkzeug.wsgi import SharedDataMiddleware
from sqlalchemy.orm import scoped_session

from mettle.web.framework import App
from mettle.settings import get_settings
from mettle.db import make_session_cls
from mettle.web.views import (logs, examples, services, pipelines, runs,
                              targets, index)


routes = [
    # The one view that returns HTML.  Everything else is JSON API.
    ('/', 'index', index.Index),

    # Show all services
    ('/api/services/', 'service_list', services.ServiceList),

    # Details on one service. 
    ('/api/services/<service_name>/', 'service_detail', services.ServiceDetail),

    # Summary for each pipeline in a service
    ('/api/services/<service_name>/pipelines/', 'pipeline_list',
     pipelines.PipelineList),

    # Details for a pipeline
    ('/api/services/<service_name>/pipelines/<pipeline_name>/',
     'pipeline_detail', pipelines.PipelineDetails),

    # List of runs for a pipeline
    ('/api/services/<service_name>/pipelines/<pipeline_name>/runs/',
     'run_list', runs.RunList),

    # Details for a pipeline run
    ('/api/services/<service_name>/pipelines/<pipeline_name>/runs/<int:run_id>/',
     'run_detail', runs.RunDetails),

    # Logs for a pipeline run.
    ('/api/services/<service_name>/pipelines/<pipeline_name>/runs/<int:run_id>/logs/',
     'run_logs', logs.Log),

    # Show all jobs in a run
    ('/api/services/<service_name>/pipelines/<pipeline_name>/runs/<int:run_id>/jobs/',
     'run_job_list', runs.RunJobs),

    # Show a job in a run, by job ID
    ('/api/services/<service_name>/pipelines/<pipeline_name>/runs/<int:run_id>/jobs/<int:job_id>/',
     'run_job_detail', runs.RunJob),

    # All log lines for a given job.
    ('/api/services/<service_name>/pipelines/<pipeline_name>/runs/<int:run_id>/jobs/<int:job_id>/logs/',
     'run_job_logs', logs.Log),

    # Show all jobs in a run for a given target
    ('/api/services/<service_name>/pipelines/<pipeline_name>/runs/<int:run_id>/targets/<target>/jobs/',
     'target_job_list', targets.TargetJobs),

]

class StaticMiddleware(SharedDataMiddleware):

    @property
    def current_app(self):
        return self.app.current_app

if 'app' not in globals():
    settings = get_settings()
    app = App(routes, settings)
    app.db = scoped_session(make_session_cls(settings.db_url))
    app = StaticMiddleware(app, {
        '/static': ('mettle', 'static')
    })

if __name__ == "__main__":
    server = pywsgi.WSGIServer(('', int(os.getenv('PORT', 8000))), app,
                               handler_class=WebSocketHandler)
    server.serve_forever()
