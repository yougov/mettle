import time
from datetime import datetime, timedelta

import utc
from croniter import croniter
import pika

from mettle.models import Pipeline, PipelineRun
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


def check_pipelines(settings):
    db = make_session_cls(settings.db_url)()
    rabbit = pika.BlockingConnection(pika.URLParameters(settings.rabbit_url))

    # connect to database
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
            print "target_time", target_time
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

    # for any that aren't yet in the database, create them.

    # announce any pipeline runs that do not yet have an ack time. 


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

        # Only announce the run if we can actually save it.  We'll
        # need the run ID as part of the announcement anyway.
        db.commit()
        print "Created new pipeline run", run.id


def check_jobs(settings):

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


def cleanup_logs(settings):
    # Delete old logs (older than max_log_days)
    pass


def main():
    settings = get_settings()
    while True:
        print "Checking pipelines"
        check_pipelines(settings)
        check_jobs(settings)
        cleanup_logs(settings)
        print "Sleeping for %s seconds" % settings.timer_sleep_secs
        time.sleep(settings.timer_sleep_secs)


if __name__ == '__main__':
    main()
