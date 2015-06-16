from spa import JSONResponse

from mettle.web.framework import ApiView
from mettle.models import Job, PipelineRun, Pipeline, Service


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
        routing_key = ('services.%s.pipelines.%s.runs.%s.targets.%s.jobs.*' %
                       (service_name, pipeline_name, run_id, target))
        self.bind_queue_to_websocket(exchange, [routing_key])

