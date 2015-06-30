import json
import logging

import utc
import pika
import isodate
from sqlalchemy.exc import OperationalError
from sqlalchemy.orm.exc import NoResultFound, MultipleResultsFound

from mettle.settings import get_settings
from mettle.models import Service, Pipeline, PipelineRun, PipelineRunNack, Job, Checkin
from mettle.lock import lock_and_announce_job
from mettle.db import make_session_cls
from mettle.notify import notify_failed_run
import mettle_protocol as mp


logger = logging.getLogger(__name__)
logger.setLevel(logging.INFO)

def on_announce_service(settings, db, data):
    logger.info("Service announced: {service}".format(**data))
    try:
        service = db.query(Service).filter_by(name=data['service']).one()
    except NoResultFound:
        service = Service(
            name=data['service'],
            updated_by='dispatcher',
        )
        db.add(service)

    service.pipeline_names = data['pipeline_names']

    # now disable any pipelines linked to this service that weren't included in
    # this announcement.  We don't do the inverse though... Once deactivated, a
    # pipeline must be manually re-activated in the UI.
    for p in service.pipelines:
        if p.name not in service.pipeline_names:
            p.active = False


def on_pipeline_run_ack(settings, rabbit, db, data):
    logger.info("Pipeline run ack {service}:{pipeline}:{run_id}".format(**data))
    run = db.query(PipelineRun).filter_by(id=data['run_id']).one()

    if run.ack_time is None:
        run.ack_time = utc.now()
        run.targets = data['targets']
        run.target_parameters = data.get('target_parameters', {})

    if run.is_ended(db):
        if run.end_time is None:
            run.end_time = utc.now()
            if run.all_targets_succeeded(db):
                run.succeeded = True
    else:
        for target in run.get_ready_targets(db):
            job = run.make_job(db, target)
            if job:
                lock_and_announce_job(db, rabbit, job)


def on_pipeline_run_nack(settings, rabbit, db, data):
    logger.info("Pipeline run nack {service}:{pipeline}:{run_id}".format(**data))
    run = db.query(PipelineRun).filter_by(id=data['run_id']).one()

    # create a new nack record.
    if data['reannounce_time'] is None:
        rtime = None
        # If reannounce_time is None, then give up on this pipeline run.
        run.ack_time = utc.now()
        run.end_time = utc.now()
    else:
        rtime = isodate.parse_datetime(data['reannounce_time'])

    db.add(PipelineRunNack(
        pipeline_run=run,
        message=data['message'],
        reannounce_time=rtime,
    ))


def on_job_claim(settings, rabbit, db, data, corr_id):
    try:
        job = db.query(Job).filter_by(
            id=data['job_id'],
            start_time=None,
        ).one()
        job.start_time = isodate.parse_datetime(data['start_time'])
        job.expires = isodate.parse_datetime(data['expires'])
        job.assigned_worker = data['worker_name']
        logger.info("Job claim %s:%s:%s:%s" % (
            job.pipeline_run_id,
            job.target,
            job.id,
            job.assigned_worker,
        ))
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
    job.succeeded = data.get('succeeded') or False
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

    # Force the job update to be committed/published before we start making any
    # changes to the run.
    db.commit()

    if run.end_time is None:
        if run.target_is_failed(db, job.target):
            notify_failed_run(db, run)
            run.end_time = end_time
        elif run.is_ended(db):
            if run.all_targets_succeeded(db):
                run.succeeded = True
            run.end_time = end_time


def main():
    settings = get_settings()

    rabbit_conn = pika.BlockingConnection(pika.URLParameters(settings.rabbit_url))
    rabbit = rabbit_conn.channel()
    mp.declare_exchanges(rabbit)
    queue_name = 'mettle_dispatcher'


    rabbit.queue_declare(queue=queue_name, exclusive=False,
                         durable=True)
    rabbit.queue_bind(exchange=mp.ANNOUNCE_SERVICE_EXCHANGE,
                      queue=queue_name, routing_key='#')
    rabbit.queue_bind(exchange=mp.ACK_PIPELINE_RUN_EXCHANGE,
                      queue=queue_name, routing_key='#')
    rabbit.queue_bind(exchange=mp.NACK_PIPELINE_RUN_EXCHANGE,
                      queue=queue_name, routing_key='#')
    rabbit.queue_bind(exchange=mp.CLAIM_JOB_EXCHANGE,
                      queue=queue_name, routing_key='#')
    rabbit.queue_bind(exchange=mp.END_JOB_EXCHANGE,
                      queue=queue_name, routing_key='#')
    rabbit.queue_bind(exchange=settings.dispatcher_ping_exchange,
                      queue=queue_name,
                      routing_key='timer')

    Session = make_session_cls(settings.db_url)

    for method, properties, body in rabbit.consume(queue=queue_name):
        db = Session()
        if method.exchange == mp.ANNOUNCE_SERVICE_EXCHANGE:
            on_announce_service(settings, db, json.loads(body))
        elif method.exchange == mp.ACK_PIPELINE_RUN_EXCHANGE:
            on_pipeline_run_ack(settings, rabbit, db, json.loads(body))
        elif method.exchange == mp.NACK_PIPELINE_RUN_EXCHANGE:
            on_pipeline_run_nack(settings, rabbit, db, json.loads(body))
        elif method.exchange == mp.CLAIM_JOB_EXCHANGE:
            on_job_claim(settings, rabbit, db, json.loads(body),
                         properties.correlation_id)
        elif method.exchange == mp.END_JOB_EXCHANGE:
            on_job_end(settings, rabbit, db, json.loads(body))
        # get messages from process timer restart queue
        elif method.exchange == settings.dispatcher_ping_exchange:
            db.merge(Checkin(proc_name='dispatcher', time=utc.now()))
        db.commit()
        rabbit.basic_ack(method.delivery_tag)

if __name__ == '__main__':
    main()
