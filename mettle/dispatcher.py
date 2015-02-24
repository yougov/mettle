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

    if run.ack_time is None:
        run.ack_time = utc.now()
        run.targets = data['targets']

    if run.is_ended(db):
        run.end_time = utc.now()
        if run.all_targets_succeeded(db):
            run.succeeded = True
    else:
        for target in run.get_ready_targets(db):
            job = run.make_job(db, target)
            if job:
                lock_and_announce_job(db, rabbit, job)


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
    end_time = isodate.parse_datetime(data['end_time'])
    job = db.query(Job).filter_by(id=data['job_id']).one()
    job.end_time = end_time
    job.succeeded = data['succeeded']
    run = job.pipeline_run

    if job.succeeded:
        # See if this job was a dependency for any other targets.  If so, check
        # if they're ready to be run now.  If they are, kick them off.
        depending_targets = [t for t, deps in run.targets.items() if job.target
                            in deps]
        if depending_targets:
            # Make sure just-completed job state is saved before we query
            db.commit()
            for target in depending_targets:
                if run.target_is_ready(db, target):
                    new_job = run.make_job(db, target)
                    if new_job:
                        logger.info('Job %s chained from %s' % (new_job.id,
                                                                job.id))
                        lock_and_announce_job(db, rabbit, new_job)

    if run.end_time is None and run.is_ended(db):
        run.end_time = end_time
        if run.all_targets_succeeded(db):
            run.succeeded = True


def main():
    settings = get_settings()

    rabbit_conn = pika.BlockingConnection(pika.URLParameters(settings.rabbit_url))
    rabbit = rabbit_conn.channel()
    mp.declare_exchanges(rabbit)
    queue_name = 'mettle_dispatcher'
    rabbit.queue_declare(queue=queue_name, exclusive=False,
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
