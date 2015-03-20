import pika

from mettle.web.framework import JSONResponse, ApiView
from mettle.web.rabbit import state_message_stream
from mettle.models import JobLogLine, Job, PipelineRun, Pipeline, Service


class RunList(ApiView):
    def get(self, service_name, pipeline_name):
        service = self.db.query(Service).filter_by(name=service_name).one()
        pipeline = self.db.query(Pipeline).filter_by(service=service,
                                                      name=pipeline_name).one()
        runs = self.db.query(PipelineRun).filter_by(pipeline=pipeline)
        return JSONResponse(dict(objects=[r.as_dict() for r in runs]))

    def websocket(self, service_name, pipeline_name):
        settings = self.app.settings
        exchange = settings['state_exchange']
        routing_key = '%s.%s.*' % (service_name, pipeline_name)
        self.bind_queue_to_websocket(exchange, routing_key)


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
        routing_key = '%s.%s.%s' % (service_name, pipeline_name, run_id)
        self.bind_queue_to_websocket(exchange, routing_key)


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
        routing_key = '%s.%s.%s.jobs.*.*' % (service_name,
                                              pipeline_name,
                                              run_id)
        self.bind_queue_to_websocket(exchange, routing_key)



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
        routing_key = '%s.%s.%s.nacks.*' % (service_name, pipeline_name, run_id)
        self.bind_queue_to_websocket(exchange, routing_key)


class RunJob(ApiView):
    def get(self, service_name, pipeline_name, run_id, job_id):

        job = self.db.query(Job).join(
            PipelineRun).join(Pipeline).join(Service).filter(
                Service.name==service_name,
                PipelineRun.pipeline_id==Pipeline.id,
                Job.pipeline_run_id==run_id,
                Job.id==job_id
            ).one()

        return JSONResponse(job.as_dict())
