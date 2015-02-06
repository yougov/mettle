import time
from datetime import datetime, timedelta

import utc
from croniter import croniter
import pika

from mettle.models import Pipeline, PipelineRun, Job, JobLogLine
from mettle.settings import get_settings
from mettle.db import make_session_cls, parse_pgurl
from mettle.protocol import announce_pipeline_run


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
    print "Checking pipelines."

    pipelines = db.query(Pipeline).filter(
        Pipeline.active==True,
        Pipeline.crontab!=None,
    )

    # for each active pipeline, look back up to lookback_days, and see which
    # pipeline runs it should have created.
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
    runs = db.query(PipelineRun).filter(
        PipelineRun.target_time>start,
        PipelineRun.ack_time==None,
    )

    for run in runs:
        announce_pipeline_run(run, rabbit)


def ensure_pipeline_run(db, pipeline, target_time):

    run = db.query(PipelineRun).filter(
        PipelineRun.pipeline==pipeline,
        PipelineRun.target_time==target_time,
        PipelineRun.ack_time==None,
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
        db.commit()
        print "Created new pipeline run", run.id


def check_jobs(db, rabbit):
    print "Checking jobs."

    # find any in_progress jobs whose expiration is in the past, and who haven't
    # had any log messages in X minutes.  Mark them as failed.
        # If a job has any retries remaining, make new job, with 
        # (new.retries = old.retries - 1), and all the other parameters the
        # same.
            # Lock the new job row
            # Announce the new job
            # Unlock the new job row

            # The lock ensures that we never have both the timer and the
            # dispatcher announce the same job.  Those announcements are the
            # only messages sent by both components.

        # If a job is expired and out of retries and no longer logging, mark it
        # as failed, and send an email to the pipeline's notification list to
        # let them know there was an unrecoverable problem.

        # If a job is expired and still logging, whether out of retries or not,
        # then send a notice, but don't expire it yet.  Yes, these notices are
        # going to pile up, but that should incentivize the owners to put a
        # better estimate on the expiration time.
    pass


def cleanup_logs(settings, db):
    print "Cleaning up old logs."
    cutoff_time = utc.now() - timedelta(days=settings.max_log_days)
    db.query(JobLogLine).filter(
        JobLogLine.received_time<cutoff_time
    ).delete(synchronize_session=False)
    db.commit()


def do_scheduled_tasks(settings):
    start_time = utc.now()
    db = make_session_cls(settings.db_url)()
    rabbit_conn = pika.BlockingConnection(pika.URLParameters(settings.rabbit_url))
    rabbit = rabbit_conn.channel()

    check_pipelines(settings, db, rabbit)
    check_jobs(db, rabbit)
    cleanup_logs(settings, db)
    run_time = utc.now() - start_time
    print ("Finished scheduled tasks.  Took %s seconds" %
           run_time.total_seconds())


def main():
    settings = get_settings()
    while True:
        do_scheduled_tasks(settings)
        print "Sleeping for %s seconds" % settings.timer_sleep_secs
        time.sleep(settings.timer_sleep_secs)


if __name__ == '__main__':
    main()
