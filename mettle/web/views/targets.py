import json

from sqlalchemy.orm.attributes import InstrumentedAttribute
from spa import JSONResponse

from mettle.web.framework import ApiView
from mettle.models import Job, PipelineRun, Pipeline, Service


class TargetJobs(ApiView):
    def get_jobs(self, service_name, pipeline_name, run_id, target):
        return self.db.query(Job).join(
            PipelineRun).join(Pipeline).join(Service).filter(
                Service.name==service_name,
                Pipeline.name==pipeline_name,
                PipelineRun.pipeline_id==Pipeline.id,
                Job.pipeline_run_id==run_id,
                Job.target==target,
            ).order_by(Job.id.desc())

    def get(self, *args, **kwargs):
        return JSONResponse({
            'objects': [j.as_dict() for j in self.get_jobs(*args, **kwargs)]
        })

    def websocket(self, service_name, pipeline_name, run_id, target):
        for j in self.get_jobs(service_name, pipeline_name, run_id, target):
            self.ws.send(json.dumps(j.as_dict()))

        settings = self.app.settings
        exchange = settings['state_exchange']
        routing_key = ('services.%s.pipelines.%s.runs.%s.targets.%s.jobs.*' %
                       (service_name, pipeline_name, run_id, target))
        self.bind_queue_to_websocket(exchange, [routing_key])

    def on_rabbit_message(self, ch, method, props, body):
        # The as_dict() method for this particular model doesn't make any extra
        # requests, so this should be cheap.  If it ever changes we might need
        # to revisit this.
        data = json.loads(body)

        # there may be keys in the dict that don't directly correspond to model
        # attributes.  filter them out, then feed the rest into a new model
        # instance
        model_attrs = {}
        for k, v in data.items():
            attr = getattr(Job, k, None)
            if isinstance(attr, InstrumentedAttribute):
                model_attrs[k] = v
        job = Job(**model_attrs)
        self.ws.send(json.dumps(job.as_dict()))
