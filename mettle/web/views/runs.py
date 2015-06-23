import json
import logging

import iso8601
from spa import JSONResponse
from sqlalchemy.orm.attributes import InstrumentedAttribute

from mettle.web.framework import ApiView
from mettle.models import Job, PipelineRun, PipelineRunNack, Pipeline, Service

logging.basicConfig()

class RunList(ApiView):
    def get(self, service_name, pipeline_name):
        service = self.db.query(Service).filter_by(name=service_name).one()
        pipeline = self.db.query(Pipeline).filter_by(service=service,
                                                      name=pipeline_name).one()
        runs = self.db.query(PipelineRun).filter_by(pipeline=pipeline).order_by('-pipeline_runs.id')
        return JSONResponse(dict(objects=[r.as_dict() for r in runs]))

    def websocket(self, service_name, pipeline_name):
        settings = self.app.settings
        exchange = settings['state_exchange']
        routing_key = 'services.%s.pipelines.%s.runs.*' % (service_name, pipeline_name)
        self.bind_queue_to_websocket(exchange, [routing_key])

    def post(self, service_name, pipeline_name):
        service = self.db.query(Service).filter_by(name=service_name).one()
        pipeline = self.db.query(Pipeline).filter_by(service=service,
                                                     name=pipeline_name).one()

        data = self.request.json()
        target_time = iso8601.parse_date(data['target_time'])
        run = PipelineRun(
            pipeline=pipeline,
            started_by=self.request.session['username'],
            target_time=target_time,
        )
        self.db.add(run)
        self.db.commit()

        url = self.app.url('run_detail', dict(
            service_name=service_name,
            pipeline_name=pipeline_name,
            run_id=run.id,
        ))

        return JSONResponse(run.as_dict(), headers={'Location': url},
                            status=302)


class RunDetails(ApiView):
    def get(self, service_name, pipeline_name, run_id):
        run = self.db.query(PipelineRun).join(Pipeline).join(Service).filter(
            Service.name==service_name,
            Pipeline.name==pipeline_name,
            Pipeline.id==PipelineRun.pipeline_id,
            PipelineRun.id==run_id,
        ).one()
        data = run.as_dict()
        data['jobs'] = [j.as_dict() for j in run.jobs]
        data['pipeline'] = run.pipeline.as_dict()
        return JSONResponse(data)

    def websocket(self, service_name, pipeline_name, run_id):
        settings = self.app.settings
        exchange = settings['state_exchange']
        routing_key = 'services.%s.pipelines.%s.runs.%s' % (service_name, pipeline_name, run_id)
        self.bind_queue_to_websocket(exchange, [routing_key])


class RunJobs(ApiView):
    def get(self, service_name, pipeline_name, run_id):

        jobs = self.db.query(Job).join(
            PipelineRun).join(Pipeline).join(Service).filter(
                Service.name==service_name,
                Pipeline.name==pipeline_name,
                PipelineRun.pipeline_id==Pipeline.id,
                Job.pipeline_run_id==run_id,
            )

        return JSONResponse({
            'jobs': [j.as_dict() for j in jobs]
        })

    def websocket(self, service_name, pipeline_name, run_id):
        settings = self.app.settings
        exchange = settings['state_exchange']
        routing_key = ('services.%s.pipelines.%s.runs.%s.targets.*.jobs.*' %
                       (service_name, pipeline_name, run_id))
        self.bind_queue_to_websocket(exchange, [routing_key])



class RunNacks(ApiView):
    def get(self, service_name, pipeline_name, run_id):

        nacks = self.db.query(PipelineRunNack).join(
            PipelineRun).join(Pipeline).join(Service).filter(
                Service.name==service_name,
                Pipeline.name==pipeline_name,
                PipelineRun.pipeline_id==Pipeline.id,
                PipelineRunNack.pipeline_run_id==run_id,
            )

        return JSONResponse({
            'nacks': [j.as_dict() for j in nacks]
        })

    def websocket(self, service_name, pipeline_name, run_id):
        settings = self.app.settings
        exchange = settings['state_exchange']
        routing_key = 'services.%s.pipelines.%s.runs.%s.nacks.*' % (service_name, pipeline_name, run_id)
        self.bind_queue_to_websocket(exchange, [routing_key])


class RunJob(ApiView):
    def get_job(self, service_name, pipeline_name, run_id, job_id):
        q = self.db.query(Job).join(
                PipelineRun).join(Pipeline).join(Service).filter(
                    Service.name==service_name,
                    PipelineRun.pipeline_id==Pipeline.id,
                    Job.pipeline_run_id==run_id,
                    Job.id==job_id
                )
        return q.one()

    def get(self, *args, **kwargs):
        return JSONResponse(self.get_job(*args, **kwargs).as_dict())

    def websocket(self, service_name, pipeline_name, run_id, job_id):
        job = self.get_job(service_name, pipeline_name, run_id, job_id)
        self.ws.send(json.dumps(job.as_dict()))

        exchange = self.app.settings['state_exchange']
        routing_key = ('services.%s.pipelines.%s.runs.%s.jobs.%s' %
                       (service_name, pipeline_name, run_id, job_id))

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
