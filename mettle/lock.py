from sqlalchemy.exc import OperationalError

from mettle.models import PipelineRun, Job
import mettle_protocol as mp



def lock_and_announce_run(db, rabbit, run):
    # When we announce this run, some worker is going to pick it up and
    # actually start doing work.  We don't want to allow a situation where
    # both the timer and the dispatcher could announce the same run and end
    # up with duplicate work being done.  So before announcing, lock the
    # row.  If we fail to acquire the lock, that means that the other proc
    # is already announcing the run, so we can skip it.

    try:
        with db.begin(subtransactions=True):
            db.query(PipelineRun).filter(
                PipelineRun.id==run.id
            ).with_lockmode('update_nowait').one()
            pipeline = run.pipeline
            mp.announce_pipeline_run(rabbit, pipeline.service.name,
                                     pipeline.name, run.target_time.isoformat(),
                                     run.id)

        # One would think that the "with db.begin()" context manager would
        # make this commit unnecessary, but testing shows that the row lock
        # will still be held unless we commit here.
        db.commit()
    except OperationalError:
        db.rollback()
        print "PipelineRun %s already locked.  Skipping." % run.id


def lock_and_announce_job(db, rabbit, job):
    # When we announce this job, some worker is going to pick it up and
    # actually start doing work.  We don't want to allow a situation where
    # both the timer and the dispatcher could announce the same job and end
    # up with duplicate work being done.  So before announcing, lock the
    # row.  If we fail to acquire the lock, that means that the other proc
    # is already announcing the job, so we can skip it.

    try:
        with db.begin(subtransactions=True):
            db.query(Job).filter(
                Job.id==job.id,
                Job.start_time==None
            ).with_lockmode('update_nowait').one()
            run = job.pipeline_run
            pipeline = run.pipeline
            mp.announce_job(rabbit, pipeline.service.name, pipeline.name,
                            run.target_time.isoformat(), job.target, job.id)

        # One would think that the "with db.begin()" context manager would
        # make this commit unnecessary, but testing shows that the row lock
        # will still be held unless we commit here.
        db.commit()
    except OperationalError:
        db.rollback()
        print "Job %s already locked.  Skipping." % job.id

