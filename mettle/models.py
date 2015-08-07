import datetime
import logging
from collections import OrderedDict

from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.schema import Index, UniqueConstraint
from sqlalchemy.dialects.postgresql import (ARRAY, JSON)
from sqlalchemy import (Column, Integer, Text, ForeignKey, ForeignKeyConstraint,
                        DateTime, Boolean, func, CheckConstraint)
from sqlalchemy.ext.mutable import MutableDict
from sqlalchemy.sql.expression import text
from sqlalchemy.orm import relationship, backref, validates
from croniter import croniter
import utc

import mettle_protocol as mp


Base = declarative_base()

logging.basicConfig()
logger = logging.getLogger(__name__)
logger.setLevel(logging.INFO)


class Service(Base):
    __tablename__ = 'services'
    id = Column(Integer, primary_key=True)
    name = Column(Text, nullable=False)
    description = Column(Text)
    updated_by = Column(Text, nullable=False)

    # TODO: once all services have this field filled in, update this to
    # nullable=False, and create a migration to match.
    pipeline_names = Column(ARRAY(Text))

    notifications = relationship("Notification", lazy='dynamic',
                                 backref=backref('service'))

    @validates('name')
    def validate_name(self, key, name):
        # Ensure that the name has no characters that have special meanings in
        # RabbitMQ routing keys.
        assert '.' not in name
        assert '*' not in name
        assert '#' not in name
        return name

    __table_args__ = (
        UniqueConstraint('name'),
    )

    def as_dict(self):
        return dict(id=self.id,
                    name=self.name,
                    description=self.description,
                    updated_by=self.updated_by,
                    pipeline_names=self.pipeline_names)

    def __repr__(self):
        return 'Service <%s>' % self.name


class NotificationList(Base):
    __tablename__ = 'notification_lists'
    id = Column(Integer, primary_key=True)
    name = Column(Text, nullable=False)
    recipients = Column(ARRAY(Text), nullable=False)
    updated_by = Column(Text, nullable=False)
    def __repr__(self):
        return 'NotificationList <%s>' % self.name


class Pipeline(Base):
    __tablename__ = 'pipelines'

    DEFAULT_RETRIES = 3

    id = Column(Integer, primary_key=True)
    name = Column(Text, nullable=False)
    service_id = Column(Integer, ForeignKey('services.id'), nullable=False)
    notification_list_id = Column(Integer, ForeignKey('notification_lists.id'),
                                  nullable=False)
    updated_by = Column(Text, nullable=False)
    active = Column(Boolean, nullable=False, server_default=text('true'))

    retries = Column(Integer, default=DEFAULT_RETRIES)

    service = relationship("Service", backref=backref('pipelines', order_by=name))
    notification_list = relationship('NotificationList',
                                     backref=backref('pipelines', order_by=name))

    # A pipeline must have either a crontab or a trigger pipeline, but not both.
    crontab = Column(Text)
    chained_from_id = Column(Integer, ForeignKey('pipelines.id'))
    chained_from = relationship("Pipeline", remote_side=id, backref='chains_to')

    runs = relationship("PipelineRun", lazy='dynamic',
                                 backref=backref('pipelines'))

    def next_run_time(self):
        if self.chained_from:
            return self.chained_from.next_run_time()
        schedule = croniter(self.crontab, utc.now())
        return schedule.get_next(datetime.datetime)

    def last_run_time(self):
        last_run = self.runs.order_by(PipelineRun.target_time.desc()).first()
        if last_run:
            return last_run.target_time

    @validates('name')
    def validate_name(self, key, name):
        # Ensure that the name has no characters that have special meanings in
        # RabbitMQ routing keys.
        assert '.' not in name
        assert '*' not in name
        assert '#' not in name
        return name

    @validates('crontab')
    def validate_crontab(self, key, cronspec):
        if cronspec is not None:
            # If the cronspec is not parseable, croniter will raise an exception
            # here.
            croniter(cronspec, utc.now())
        return cronspec

    __table_args__ = (
        UniqueConstraint('name', 'service_id'),
        UniqueConstraint('id', 'service_id'), # needed for composite FK
        CheckConstraint('crontab IS NOT NULL OR chained_from_id IS NOT NULL',
                        name='crontab_or_pipeline_check'),
        CheckConstraint('NOT (crontab IS NOT NULL AND chained_from_id IS NOT NULL)',
                        name='crontab_and_pipeline_check'),
    )

    def __repr__(self):
        return 'Pipeline <%s>' % self.name

    def as_dict(self):
        next_time = self.next_run_time()
        last_time = self.last_run_time()
        return OrderedDict(
            id=self.id,
            name=self.name,
            service_id=self.service_id,
            service_name=self.service.name, # can cause extra query!
            notification_list_id=self.notification_list_id,
            updated_by=self.updated_by,
            active=self.active,
            retries=self.retries,
            crontab=self.crontab,
            chained_from_id=self.chained_from_id,
            next_run_time=next_time.isoformat() if next_time else None,
            last_run_time=last_time.isoformat() if last_time else None,
        )


class PipelineRun(Base):
    __tablename__ = 'pipeline_runs'
    id = Column(Integer, primary_key=True)
    pipeline_id = Column(Integer, ForeignKey('pipelines.id'), nullable=False)
    target_time = Column(DateTime(timezone=True), nullable=False)
    created_time = Column(DateTime(timezone=True), nullable=False,
                  server_default=func.now())
    succeeded = Column(Boolean, nullable=False, default=False,
                       server_default=text('false'))
    started_by = Column(Text, nullable=False) # username or 'timer'

    chained_from_id = Column(Integer, ForeignKey('pipeline_runs.id'))

    # These fields are set when we get an ack from the ETL service
    ack_time = Column(DateTime(timezone=True))
    targets = Column(MutableDict.as_mutable(JSON), default={})
    target_parameters = Column(MutableDict.as_mutable(JSON), default={})

    # end_time is set by dispatcher after it has heard in from all job runs
    end_time = Column(DateTime(timezone=True))

    pipeline = relationship("Pipeline", backref=backref('pipeline_runs',
                                                        order_by=created_time))

    chained_from = relationship("PipelineRun", backref=backref('chains_to'),
                               remote_side=id)

    def get_announce_time(self):
        if self.nacks:
            return max(n.reannounce_time for n in self.nacks)
        return None

    def is_ended(self, db):
        if self.ack_time is None:
            return False
        return all(self.target_is_ended(db, t) for t in self.targets)

    def is_failed(self, db):
        return any(self.target_is_failed(db, t) for t in self.targets)

    def all_targets_succeeded(self, db):
        return all(self.target_is_succeeded(db, t) for t in self.targets)

    def target_is_succeeded(self, db, target):
        job = db.query(Job).filter(Job.pipeline_run==self,
                                   Job.target==target,
                                   Job.succeeded==True).first()
        return job is not None

    def target_is_failed(self, db, target):
        failure_count = db.query(Job).filter(Job.pipeline_run==self,
                                             Job.target==target,
                                             Job.end_time!=None,
                                             Job.succeeded==False).count()
        return failure_count >= self.pipeline.retries

    def target_is_ended(self, db, target):
        return (self.target_is_succeeded(db, target) or
                self.target_is_failed(db, target))

    def target_is_in_progress(self, db, target):
        job = db.query(Job).filter(Job.pipeline_run==self,
                                   Job.target==target,
                                   Job.end_time==None).first()
        return job is not None

    def target_deps_met(self, db, target):
        for dep in self.targets[target]:
            if not self.target_is_succeeded(db, dep):
                return False
        return True

    def target_is_ready(self, db, target):
        # Return true if the target meets these conditions:
        # 1. Is not ended.
        # 2. Does not already have an in-progress job in the DB.
        # 3. If it has dependencies, there is a successful job in the DB whose
        # target provides that dependency.
        if self.target_is_ended(db, target):
            return False
        if self.target_is_in_progress(db, target):
            return False

        return self.target_deps_met(db, target)

    def get_ready_targets(self, db):
        return [t for t in self.targets if self.target_is_ready(db, t)]

    def make_job(self, db, target):
        target_params = (self.target_parameters.get(target) if
                         self.target_parameters else None)
        job = Job(
            pipeline_run=self,
            target=target,
            target_parameters=target_params,
        )
        db.add(job)
        try:
            db.commit()
        except IntegrityError as e:
            logger.error(str(e))
            db.rollback()
            return None
        return job

    @validates('targets')
    def validate_targets(self, key, targets):
        mp.validate_targets_graph(targets)
        return targets

    __table_args__ = (
        Index('unique_run_in_progress', pipeline_id, target_time,
              postgresql_where=end_time==None, unique=True),

        # Prevent duplicate runs of the same pipeline chained from the same
        # previous pipeline.
        Index('unique_run_chained_from', pipeline_id, chained_from_id,
              unique=True),
        # Can't have a ack time without targets, even if it's an empty list
        CheckConstraint('NOT (ack_time IS NOT NULL AND targets IS NULL)',
                        name='run_ack_without_targets_check'),
        # Can't have a end time without an ack time
        CheckConstraint('NOT (end_time IS NOT NULL AND ack_time IS NULL)',
                        name='run_end_without_ack_check'),
        UniqueConstraint('id', 'pipeline_id'), # needed for composite FK
    )

    def as_dict(self):
        return OrderedDict(
            id=self.id,
            pipeline_id=self.pipeline_id,
            target_time=self.target_time.isoformat(),
            created_time=self.created_time.isoformat(),
            succeeded=self.succeeded,
            started_by=self.started_by,
            ack_time=self.ack_time.isoformat() if self.ack_time else None,
            targets=self.targets,
            end_time=self.end_time.isoformat() if self.end_time else None,
        )


class PipelineRunNack(Base):
    __tablename__ = 'pipeline_runs_nacks'
    id = Column(Integer, primary_key=True)
    pipeline_run_id = Column(Integer, ForeignKey('pipeline_runs.id'),
                             nullable=False)
    created_time = Column(DateTime(timezone=True), nullable=False,
                  server_default=func.now())
    message = Column(Text, nullable=False)

    # If a nack message specifies that a run should not be reannounced, this
    # column will be left null.
    reannounce_time = Column(DateTime(timezone=True))

    pipeline_run = relationship("PipelineRun", backref=backref('nacks',
                                                               order_by=created_time))


class Job(Base):
    __tablename__ = 'jobs'
    id = Column(Integer, primary_key=True)

    # These fields are populated when the job record is first created.
    pipeline_run_id = Column(Integer, ForeignKey('pipeline_runs.id'),
                             nullable=False)
    target = Column(Text, nullable=False)
    target_parameters = Column(MutableDict.as_mutable(JSON), default={})
    succeeded = Column(Boolean, nullable=False, default=False,
                       server_default=text('false'))
    created_time = Column(DateTime(timezone=True), nullable=False,
                  server_default=func.now())

    # These fields are populated when we receive an ack for the job from the ETL
    # service.
    start_time = Column(DateTime(timezone=True))
    assigned_worker = Column(Text)
    expires = Column(DateTime(timezone=True))

    # And end_time is populated either when we receive a job_end message from
    # the ETL service, or the timer proc decides that the job has timed out.
    end_time = Column(DateTime(timezone=True))

    pipeline_run = relationship("PipelineRun", backref=backref('jobs',
                                                        order_by=created_time))

    __table_args__ = (
        # Only allow one non-ended job for a target at a time.
        Index('unique_job_in_progress', pipeline_run_id, target,
              postgresql_where=end_time==None, unique=True),
        # Can't be succeeded unless you have an end time
        CheckConstraint('NOT (succeeded AND end_time IS NULL)',
                        name='job_succeeded_without_end_check'),
        # Can't have an end time without a start time.
        CheckConstraint('NOT (end_time IS NOT NULL AND start_time IS NULL)',
                        name='job_end_without_start_check'),
        # Can't have a start time without a hostname
        CheckConstraint('NOT (start_time IS NOT NULL AND assigned_worker IS NULL)',
                        name='job_start_without_worker_check'),
        # Can't have a start time without a expire time
        CheckConstraint('NOT (start_time IS NOT NULL AND expires IS NULL)',
                        name='job_start_without_expire_check'),
        UniqueConstraint('id', 'pipeline_run_id'), # needed for composite FK
    )

    def as_dict(self):
        stime = self.start_time.isoformat() if self.start_time else None
        etime = self.end_time.isoformat() if self.end_time else None
        expires = self.expires.isoformat() if self.expires else None

        # A bit ugly.  split these into separate DB columns?
        host = None
        pid = None
        if self.assigned_worker:
            host, pid = self.assigned_worker.split('_')[:2]
            pid = int(pid)

        return dict(
            id=self.id,
            pipeline_run_id=self.pipeline_run_id,
            target=self.target,
            succeeded=self.succeeded,
            created_time=self.created_time.isoformat(),
            start_time=stime,
            end_time=etime,
            assigned_worker=self.assigned_worker,
            expires=expires,
            host=host,
            pid=pid,
        )

    def get_queue(self, service_name):
        if self.target_parameters is None:
            return mp.service_queue_name(service_name)

        return self.target_parameters.get('queue',
                                          mp.service_queue_name(service_name))



class JobLogLine(Base):
    __tablename__ = 'job_log_lines'
    id = Column(Integer, primary_key=True)
    job_id = Column(Integer, ForeignKey('jobs.id'), nullable=False)
    message = Column(Text, nullable=False)
    line_num = Column(Integer, nullable=False)
    received_time = Column(DateTime(timezone=True), nullable=False,
                           server_default=func.now())

    job = relationship("Job", backref=backref('job_log_lines',
                                              order_by=line_num))
    __table_args__ = (
        UniqueConstraint('job_id', 'line_num'),
    )

    def as_dict(self):
        # This must match the structure of the messages coming over rabbitmq.
        job = self.job
        run = job.pipeline_run
        pipeline = run.pipeline
        service = pipeline.service
        return {
            'service': service.name,
            'pipeline': pipeline.name,
            'run_id': run.id,
            'job_id': job.id,
            'line_num': self.line_num,
            'msg': self.message,
        }

    def __repr__(self):
        return "%s - %s: %s" % (self.job_id, self.line_num, self.message)


# This table is populated by triggers on services, pipelines, and
# notification_lists
class ChangeRecord(Base):
    __tablename__ = 'change_records'
    id = Column(Integer, primary_key=True)
    table = Column(Text, nullable=False)
    row_id = Column(Integer, nullable=False)
    time = Column(DateTime(timezone=True), nullable=False,
                  server_default=func.now())
    operation = Column(Text, nullable=False)
    who = Column(Text)
    old = Column(JSON)
    new = Column(JSON)


class Notification(Base):
    __tablename__ = 'notifications'
    id = Column(Integer, primary_key=True)
    created_time = Column(DateTime(timezone=True), nullable=False,
                  server_default=func.now())

    message = Column(Text, nullable=False)

    acknowledged_by = Column(Text)
    acknowledged_time = Column(DateTime(timezone=True))

    # Notifications can be attached to services, pipelines, pipeline runs, or
    # jobs.  If you attach to one of the more specific things (e.g. Job), then
    # you must also specify the intermediate things (pipeline run, pipeline).  A
    # foreign key constraint will prevent non-sensical links.

    # Requiring the population of the intermediate FKs will make check
    # constraints and queries on notifications much simpler.
    service_id = Column(Integer, ForeignKey('services.id'), nullable=False)
    pipeline_id = Column(Integer, ForeignKey('pipelines.id'))
    pipeline_run_id = Column(Integer, ForeignKey('pipeline_runs.id'))
    job_id = Column(Integer, ForeignKey('jobs.id'))

    pipeline = relationship("Pipeline", backref=backref('notifications',
                                                        order_by=created_time,
                                                        lazy='dynamic'),
                           foreign_keys=[pipeline_id])
    pipeline_run = relationship("PipelineRun", backref=backref('notifications',
                                                               order_by=created_time),
                               foreign_keys=[pipeline_run_id])
    job = relationship("Job", backref=backref('notifications',
                                              order_by=created_time),
                       foreign_keys=[job_id])

    def as_dict(self):
        return {
            'id': self.id,
            'created_time': self.created_time.isoformat(),
            'message': self.message,
            'acknowledged_by': self.acknowledged_by,
            'acknowledged_time': (self.acknowledged_time.isoformat() if
                                  self.acknowledged_time else None),
            'service_id': self.service_id,
            'service_name': self.service.name if self.service else None,
            'pipeline_id': self.pipeline_id,
            'pipeline_name': self.pipeline.name if self.pipeline else None,
            'pipeline_run_id': self.pipeline_run_id,
            'job_id': self.job_id,
            'target': self.job.target if self.job else None,
        }

    __table_args__ = (
        # acknowledgement fields must be filled together.
        CheckConstraint(
            'NOT (acknowledged_by IS NOT NULL AND acknowledged_time IS NULL)',
            name='notification_ack_time_check'
        ),
        CheckConstraint(
            'NOT (acknowledged_time IS NOT NULL AND acknowledged_by IS NULL)',
            name='notification_ack_by_check'
        ),

        # Must provide pipeline run if you provide job.
        CheckConstraint('NOT (job_id IS NOT NULL AND pipeline_run_id IS NULL)',
                        name='notification_job_check'),

        # Must provide pipeline if you provide pipeline run.
        CheckConstraint('NOT (pipeline_run_id IS NOT NULL AND pipeline_id IS NULL)',
                        name='notification_run_check'),

        # Don't need a check constraint on pipeline+service, since service is
        # already NOT NULL

        # Prevent service/pipeline mismatches
        ForeignKeyConstraint(['service_id', 'pipeline_id'],
                             ['pipelines.service_id', 'pipelines.id']),

        # Prevent pipeline/run mismatches
        ForeignKeyConstraint(['pipeline_id', 'pipeline_run_id'],
                             ['pipeline_runs.pipeline_id', 'pipeline_runs.id']),

        # Prevent run/job mismatches
        ForeignKeyConstraint(['pipeline_run_id', 'job_id'],
                             ['jobs.pipeline_run_id', 'jobs.id']),
    )


class Checkin(Base):

    __tablename__ = 'checkins'

    proc_name = Column(Text, primary_key=True)
    time = Column(DateTime(timezone=True), nullable=False)

    def as_dict(self):
        return {
            'proc_name': self.proc_name,
            'time': self.time.isoformat(),
        }

