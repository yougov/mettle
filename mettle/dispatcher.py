# This component listens on rabbitmq for three kinds of messages
# 1. pipeline run ack messages
# 2. job ack messages
# 3. job end messages

# Upon hearing each kind of message, it will update the database and, if
# necessary, send more job messages to push the pipeline run towards completion.

# This component is designed so that it should be safe to run multiple instances
# at the same time, without duplication of jobs.

import json
import logging

import utc
import pika
import isodate
from sqlalchemy.exc import OperationalError
from sqlalchemy.orm.exc import NoResultFound

from mettle.settings import get_settings
from mettle.models import PipelineRun, Job
from mettle.lock import lock_and_announce_job
from mettle.db import make_session_cls
import mettle_protocol as mp


logger = logging.getLogger(__name__)
logger.setLevel(logging.INFO)

def on_pipeline_run_ack(settings, rabbit, db, data):
    logger.info("Pipeline run ack {service}:{pipeline}:{run_id}".format(**data))
    run = db.query(PipelineRun).filter_by(id=data['run_id']).one()

    run.ack_time = utc.now()

    run.targets = data['targets_present'] + data['targets_absent']
    missing_targets = data['targets_absent']
    if missing_targets:
        for target in data['targets_absent']:
            job = db.query(Job).filter(Job.pipeline_run_id==data['run_id'],
                                       Job.end_time==None,
                                       Job.target==target).first()
            if job is None:
                job = Job(
                    pipeline_run=run,
                    target=target,
                    retries_remaining=run.pipeline.retries,
                )
                db.add(job)
                db.commit()
                lock_and_announce_job(db, rabbit, job)
    else:
        # There are no targets to be made.  Mark the run as complete.
        run.end_time = utc.now()


def on_job_claim(settings, rabbit, db, data, corr_id):
    logger.info("Job claim %s:%s:%s" % (data['job_id'], data['worker_name'],
                                        corr_id))
    try:
        job = db.query(Job).filter_by(
            id=data['job_id'],
            start_time=None,
        ).one()
        job.start_time = isodate.parse_datetime(data['start_time'])
        job.expires = isodate.parse_datetime(data['expires'])
        job.assigned_worker = data['worker_name']
        db.commit()
        mp.grant_job(rabbit, data['worker_name'], corr_id, True)
    except (OperationalError, NoResultFound):
        db.rollback()
        logger.info(("Claim of job {job_id} by worker {worker_name} failed. "
                     "Job already claimed").format(**data))
        mp.grant_job(rabbit, data['worker_name'], corr_id, False)


def on_job_end(settings, rabbit, db, data):
    logger.info("Job end {service}:{pipeline}:{job_id}".format(**data))
    job = db.query(Job).filter_by(id=data['job_id']).one()
    job.end_time = isodate.parse_datetime(data['end_time'])
    job.succeeded = data['succeeded']


def main():
    settings = get_settings()

    rabbit_conn = pika.BlockingConnection(pika.URLParameters(settings.rabbit_url))
    rabbit = rabbit_conn.channel()
    mp.declare_exchanges(rabbit)
    queue_name = 'mettle_dispatcher'
    queue = rabbit.queue_declare(queue=queue_name, exclusive=False,
                                 durable=True)
    rabbit.queue_bind(exchange=mp.ACK_PIPELINE_RUN_EXCHANGE,
                      queue=queue_name, routing_key='#')
    rabbit.queue_bind(exchange=mp.CLAIM_JOB_EXCHANGE,
                      queue=queue_name, routing_key='#')
    rabbit.queue_bind(exchange=mp.END_JOB_EXCHANGE,
                      queue=queue_name, routing_key='#')

    Session = make_session_cls(settings.db_url)
    for method, properties, body in rabbit.consume(queue=queue_name):
        db = Session()
        if method.exchange == mp.ACK_PIPELINE_RUN_EXCHANGE:
            on_pipeline_run_ack(settings, rabbit, db, json.loads(body))
        elif method.exchange == mp.CLAIM_JOB_EXCHANGE:
            on_job_claim(settings, rabbit, db, json.loads(body),
                         properties.correlation_id)
        elif method.exchange == mp.END_JOB_EXCHANGE:
            on_job_end(settings, rabbit, db, json.loads(body))
        db.commit()
        rabbit.basic_ack(method.delivery_tag)

if __name__ == '__main__':
    main()
