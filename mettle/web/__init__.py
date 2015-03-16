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
from mettle.web.views import (logs, examples, services, pipelines, runs, index)


routes = [
    # The one view that returns HTML.  Everything else is JSON API.
    ('/', 'index', index.Index),

    # Show all services
    ('/api/services/', 'list_services', services.ServiceList),

    # Details on one service. 
    #('/api/services/<service_name>/', 'details_service', services.ServiceDetail),

    # Summary for each pipeline in a service
    ('/api/services/<service_name>/pipelines/', 'list_pipelines',
     pipelines.PipelineList),

    # Details for a pipeline
    ('/api/services/<service_name>/pipelines/<pipeline_name>/',
     'details_pipeline', pipelines.PipelineDetails),

    # List of runs for a pipeline
    ('/api/services/<service_name>/pipelines/<pipeline_name>/runs/',
     'list_runs', runs.RunList),

    # Details for a pipeline run
    ('/api/services/<service_name>/pipelines/<pipeline_name>/runs/<int:run_id>/',
     'details_run', runs.RunDetails),

    # Logs for a pipeline run.
    ('/api/services/<service_name>/pipelines/<pipeline_name>/runs/<int:run_id>/logs/',
     'logs_run', logs.Log),

    # Show all jobs in a run
    ('/api/services/<service_name>/pipelines/<pipeline_name>/runs/<int:run_id>/jobs/',
     'run_jobs', runs.RunJobs),

    # Show a job in a run, by job ID
    ('/api/services/<service_name>/pipelines/<pipeline_name>/runs/<int:run_id>/jobs/<int:job_id>/',
     'run_job', runs.RunJob),

    # Show all jobs in a run for a given target
    ('/api/services/<service_name>/pipelines/<pipeline_name>/runs/<int:run_id>/targets/<target>/',
     'run_target', runs.RunJobs),

    ('/api/services/<service_name>/pipelines/<pipeline_name>/runs/<int:run_id>/targets/<target>/logs/',
     'logs_target', logs.Log),
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
