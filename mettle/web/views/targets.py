import pika

from mettle.web.framework import JSONResponse, ApiView
from mettle.web.rabbit import state_message_stream
from mettle.models import JobLogLine, Job, PipelineRun, Pipeline, Service


class TargetJobs(ApiView):
    def get(self, service_name, pipeline_name, run_id, target):

        jobs = self.db.query(Job).join(
            PipelineRun).join(Pipeline).join(Service).filter(
                Service.name==service_name,
                Pipeline.name==pipeline_name,
                PipelineRun.pipeline_id==Pipeline.id,
                Job.pipeline_run_id==run_id,
                Job.target==target,
            )

        return JSONResponse({
            'objects': [j.as_dict() for j in jobs]
        })

    def websocket(self, service_name, pipeline_name, run_id, target):
        settings = self.app.settings
        exchange = settings['state_exchange']
        routing_key = '%s.%s.%s.jobs.%s.*' % (service_name,
                                              pipeline_name,
                                              run_id,
                                              target)
        self.bind_queue_to_websocket(exchange, routing_key)

