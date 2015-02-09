import logging
import time
from datetime import datetime, timedelta

import utc
from croniter import croniter
import pika
from mettle_protocol import declare_exchanges, announce_pipeline_run

from mettle.models import Pipeline, PipelineRun, Job, JobLogLine
from mettle.settings import get_settings
from mettle.db import make_session_cls, parse_pgurl
from mettle.lock import lock_and_announce_run, lock_and_announce_job
from mettle.email import email_pipeline_group

logger = logging.getLogger(__name__)
logger.setLevel(logging.INFO)

# Subclass croniter so it returns datetimes by default instead of floats
class crontimes(croniter):
    def get_next(self, ret_type=datetime):
        return super(crontimes, self).get_next(ret_type)
    def get_prev(self, ret_type=datetime):
        return super(crontimes, self).get_prev(ret_type)
    def get_current(self, ret_type=datetime):
        return super(crontimes, self).get_current(ret_type)
    def all_next(self, ret_type=datetime):
        return super(crontimes, self).all_next(ret_type)
    def all_prev(self, ret_type=datetime):
        return super(crontimes, self).all_prev(ret_type)
    __next__ = next = get_next


def check_pipelines(settings, db, rabbit):
    logger.info("Checking pipelines.")

    pipelines = db.query(Pipeline).filter(
        Pipeline.active==True,
        Pipeline.crontab!=None,
    )

    # Create new pipeline runs.  For each active pipeline, look back up to
    # lookback_days, and see which pipeline runs it should have created.
    now = utc.now()
    start = now - timedelta(days=settings.lookback_days)
    for pipeline in pipelines:
        for target_time in crontimes(pipeline.crontab, start):
            if target_time < now:
                ensure_pipeline_run(db, pipeline, target_time)
            else:
               break

    # Now announce all unacked pipeline runs, whether created by this timer or
    # by someone manually, or by the dispatcher (using a trigger off some other
    # run)
    unacked_runs = db.query(PipelineRun).filter(
        PipelineRun.created_time>start,
        PipelineRun.ack_time==None,
    )
    for run in unacked_runs:
        pipeline = run.pipeline
        service = pipeline.service
        target_time = run.target_time.isoformat()
        lock_and_announce_run(db, rabbit, run)

    # Finally, check for any acked runs without an end_time, and see if they're
    # actually finished.
    unended_runs = db.query(PipelineRun).filter(
        PipelineRun.created_time>start,
        PipelineRun.ack_time!=None,
        PipelineRun.end_time==None
    )
    for run in unended_runs:
        if run.is_ended(db):
            run.end_time=now


def ensure_pipeline_run(db, pipeline, target_time):
    run = db.query(PipelineRun).filter(
        PipelineRun.pipeline==pipeline,
        PipelineRun.target_time==target_time,
    ).first()
    if run is None:
        # Looks like a pipeline run in our window of time didn't get
        # created.  Do that now.
        run = PipelineRun(
            pipeline=pipeline,
            target_time=target_time,
            started_by='timer',
        )
        db.add(run)
        logger.info("Created new pipeline run %s" % run.id)


def check_jobs(settings, db, rabbit):
    logger.info("Checking jobs.")

    now = utc.now()
    expired_jobs = db.query(Job).filter(
        Job.end_time==None,
        Job.expires<now,
    )

    log_cutoff_time = now - timedelta(minutes=settings.job_log_lookback_minutes)

    for job in expired_jobs:
        recent_log_lines_count = db.query(JobLogLine).filter(
            JobLogLine.job==job,
            JobLogLine.received_time>log_cutoff_time
        ).count()
        if recent_log_lines_count:
            pipeline = job.pipeline_run.pipeline
            subj = "Job %s running past expire time." % job.target
            msg = """Job {target_time} {target}, from pipeline {pipeline} has
            passed its expire time, but is still emitting log output.  Will let
            it continue.  Please consider modifiying the service to provide a
            more accurate expiration time.""".format(
                target_time=job.pipeline_run.target_time.isoformat(),
                target=job.target,
                pipeline=pipeline.name,
            )
            email_pipeline_group(db, pipeline, subj, msg)
        else:
            # This expired job is no longer doing stuff.  As far as we can tell.
            job.end_time = now
            if job.retries_remaining > 0:
                # Make a new job, with decremented retries field.
                new_job = Job(
                    pipeline_run=job.pipeline_run,
                    target=job.target,
                    retries_remaining=job.retries_remaining - 1,
                )
                db.add(new_job)
            else:
                # No more retries.  Send a failure notification
                pipeline = job.pipeline_run.pipeline
                subj = "Job %s out of retries" % job.target
                msg = """Job {target_time} {target}, from pipeline {pipeline} has
                passed its expire time, is no longer emitting log output, and
                has no retries remaining.  You should look into it.""".format(
                    target_time=job.pipeline_run.target_time.isoformat(),
                    target=job.target,
                    pipeline=pipeline.name,
                )
                email_pipeline_group(db, pipeline, subj, msg)
    db.commit()

    # Handle jobs that haven't been acked.  They should be re-announced.  Any
    # expired ones have already been cleaned up by the time we get here.
    new_jobs = db.query(Job).filter(
        Job.start_time==None,
    )

    for job in new_jobs:
        lock_and_announce_job(db, rabbit, job)

def cleanup_logs(settings, db):
    logger.info("Cleaning up old logs.")
    cutoff_time = utc.now() - timedelta(days=settings.max_log_days)
    db.query(JobLogLine).filter(
        JobLogLine.received_time<cutoff_time
    ).delete(synchronize_session=False)


def do_scheduled_tasks(settings):
    start_time = utc.now()
    db = make_session_cls(settings.db_url)()
    rabbit_conn = pika.BlockingConnection(pika.URLParameters(settings.rabbit_url))
    rabbit = rabbit_conn.channel()
    declare_exchanges(rabbit)
    check_pipelines(settings, db, rabbit)
    check_jobs(settings, db, rabbit)
    cleanup_logs(settings, db)
    db.commit()
    run_time = utc.now() - start_time
    logger.info("Finished scheduled tasks.  Took %s seconds" %
           run_time.total_seconds())


def main():
    settings = get_settings()
    while True:
        do_scheduled_tasks(settings)
        logger.info("Sleeping for %s seconds" % settings.timer_sleep_secs)
        time.sleep(settings.timer_sleep_secs)


if __name__ == '__main__':
    main()
