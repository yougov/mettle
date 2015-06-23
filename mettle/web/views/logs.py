import json

from spa import JSONResponse

import mettle_protocol as mp

from mettle.web.framework import ApiView
from mettle.models import JobLogLine, Job, PipelineRun, Pipeline, Service


class Log(ApiView):
    """
    Return JobLogLines as json.

    Maybe be called either by GET, to return past logs, or as websocket, to
    return stream of current logs.
    """

    def get_lines(self, service_name, pipeline_name, run_id, job_id, tail=None):
        # Note that this function always returns a list, not a query object.

        lines = self.db.query(JobLogLine).join(
            Job).join(PipelineRun).join(Pipeline).join(Service).filter(
                Service.name==service_name,
                PipelineRun.pipeline_id==Pipeline.id,
                Job.pipeline_run_id==run_id,
                Job.id==job_id,
            )

        if tail is None:
            lines = list(lines.order_by(JobLogLine.job_id, JobLogLine.line_num))
        else:
            # We've been told to only return a number of the most recent lines.
            # Do that by reversing the ordering in the query, imposing a limit,
            # running the query, and then reversing the order again in Python.
            lines = lines.order_by(JobLogLine.line_num.desc())
            lines = lines.limit(tail)
            lines = reversed(list(lines))

        return lines



    def get(self, service_name, pipeline_name, run_id, job_id):
        tail = self.request.args.get('tail')
        lines = self.get_lines(service_name, pipeline_name, run_id, job_id,
                               tail)
        return JSONResponse({'lines': [l.as_dict() for l in lines]})

    def websocket(self, service_name, pipeline_name, run_id, job_id):
        # If requested, stream out the N most recent lines from the database
        # before starting the Rabbit stream.
        tail = self.request.args.get('tail')
        if tail is not None:
            lines = self.get_lines(service_name, pipeline_name, run_id, job_id,
                                   tail)
            for l in lines:
                self.ws.send(json.dumps(l.as_dict()))

        routing_key = '.'.join([
            service_name,
            pipeline_name,
            str(run_id),
            '*', # target
            str(job_id),
        ])
        self.bind_queue_to_websocket(mp.JOB_LOGS_EXCHANGE, [routing_key])
