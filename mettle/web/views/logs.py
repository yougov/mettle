import pika

import mettle_protocol as mp

from mettle.web.framework import JSONResponse, View
from mettle.models import JobLogLine, Job, PipelineRun, Pipeline, Service


class Log(View):
    """
    Return JobLogLines as json.

    Maybe be called either by GET, to return past logs, or as websocket, to
    return stream of current logs.
    """

    def get_lines(self, service_name, pipeline_name, run_id, target=None,
                  tail=None):
        # Note that this function always returns a list, not a query object.

        lines = self.db.query(JobLogLine).join(
            Job).join(PipelineRun).join(Pipeline).join(Service).filter(
                Service.name==service_name,
                PipelineRun.pipeline_id==Pipeline.id,
                Job.pipeline_run_id==run_id,
            )

        if target is not None:
            lines = lines.filter(Job.target==target)

        if tail is None:
            lines = list(lines.order_by(JobLogLine.job_id, JobLogLine.line_num))
        else:
            # We've been told to only return a number of the most recent lines.
            # Do that by reversing the ordering in the query, imposing a limit,
            # running the query, and then reversing the order again in Python.
            lines = lines.order_by(JobLogLine.job_id.desc(),
                                   JobLogLine.line_num.desc()).limit(tail)
            lines = reversed(list(lines))

        return lines



    def get(self, service_name, pipeline_name, run_id, target=None):
        tail = self.request.args.get('tail')
        lines = self.get_lines(service_name, pipeline_name, run_id, target,
                               tail)
        return JSONResponse({'lines': [l.as_dict() for l in lines]})

    def websocket(self, service_name, pipeline_name, run_id, target=None):

        routing_key = '.'.join([
            service_name,
            pipeline_name,
            str(run_id),
            mp.mq_escape(target) if target else '*',
            '*'
        ])
        settings = self.app.settings
        connection = pika.BlockingConnection(pika.URLParameters(settings.rabbit_url))
        channel = connection.channel()

        queue = channel.queue_declare(exclusive=True)
        queue_name = queue.method.queue

        channel.exchange_declare(exchange=mp.JOB_LOGS_EXCHANGE, type='topic',
                                 durable=True)
        channel.queue_bind(exchange=mp.JOB_LOGS_EXCHANGE,
                           queue=queue_name,
                           routing_key=routing_key)

        # If requested, stream out the N most recent lines from the database
        # before starting the Rabbit stream.
        tail = self.request.args.get('tail')
        already_seen = set()
        if tail is not None:
            lines = self.get_lines(service_name, pipeline_name, run_id, target,
                                   tail)
            for l in lines:
                already_seen.add((l.job_id, l.line_num))
                self.ws.send(json.dumps(l.as_dict()))


        for method, properties, body in channel.consume(queue=queue_name,
                                                        no_ack=True):
            parsed = json.loads(body)
            # Deduplicate lines that we might have just fetched from the DB.
            if (parsed['job_id'], parsed['line_num']) not in already_seen:
                self.ws.send(body)
