from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.schema import Index, UniqueConstraint
from sqlalchemy.dialects.postgresql import (ARRAY, JSON)
from sqlalchemy import (Column, Integer, Text, ForeignKey, DateTime, Boolean,
                        func, CheckConstraint, and_)
from sqlalchemy.ext.mutable import MutableDict
from sqlalchemy.sql.expression import text
from sqlalchemy.orm import relationship, backref, validates
from croniter import croniter
import utc


Base = declarative_base()


class Service(Base):
    __tablename__ = 'services'
    id = Column(Integer, primary_key=True)
    name = Column(Text, nullable=False)
    description = Column(Text)
    updated_by = Column(Text, nullable=False)

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
    id = Column(Integer, primary_key=True)
    name = Column(Text, nullable=False)
    service_id = Column(Integer, ForeignKey('services.id'), nullable=False)
    notification_list_id = Column(Integer, ForeignKey('notification_lists.id'),
                                  nullable=False)
    updated_by = Column(Text, nullable=False)
    active = Column(Boolean, nullable=False, server_default=text('true'))

    retries = Column(Integer, default=3)

    service = relationship("Service", backref=backref('pipelines', order_by=name))
    notification_list = relationship('NotificationList',
                                     backref=backref('pipelines', order_by=name))

    # A pipeline must have either a crontab or a trigger pipeline, but not both.
    crontab = Column(Text)
    chained_from_id = Column(Integer, ForeignKey('pipelines.id'))
    chained_from = relationship(lambda: Pipeline, remote_side=id,
                                backref='chains_to')

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
        CheckConstraint('crontab IS NOT NULL OR chained_from_id IS NOT NULL',
                        name='crontab_or_pipeline_check'),
        CheckConstraint('NOT (crontab IS NOT NULL AND chained_from_id IS NOT NULL)',
                        name='crontab_and_pipeline_check'),
    )

    def __repr__(self):
        return 'Pipeline <%s>' % self.name


class PipelineRun(Base):
    __tablename__ = 'pipeline_runs'
    id = Column(Integer, primary_key=True)
    pipeline_id = Column(Integer, ForeignKey('pipelines.id'), nullable=False)
    target_time = Column(DateTime(timezone=True), nullable=False)
    created_time = Column(DateTime(timezone=True), nullable=False,
                  server_default=func.now())
    started_by = Column(Text, nullable=False) # username or 'timer'

    # These fields are set when we get an ack from the ETL service
    ack_time = Column(DateTime(timezone=True))
    targets = Column(ARRAY(Text), default=[])

    # end_time is set by dispatcher after it has heard in from all job runs
    end_time = Column(DateTime(timezone=True))

    pipeline = relationship("Pipeline", backref=backref('pipeline_runs',
                                                        order_by=created_time))

    def is_ended(self, db):
        if self.ack_time is None:
            return False
        return all(self.target_is_ended(db, t) for t in self.targets)

    def target_is_ended(self, db, target):
        # A target is ended if we have either:
            # 1. A successful job in this pipeline run for that target
            # 2. The count of failed jobs for that target, in this run, is greater
            # than or equal to pipeline.retries.
        succeeded = db.query(Job).filter(Job.pipeline_run==self,
                                         Job.succeeded==True).first()
        if succeeded:
            return True

        failure_count = db.query(Job).filter(Job.pipeline_run==self,
                                             Job.target==target,
                                             Job.end_time!=None,
                                             Job.succeeded==False).count()
        if failure_count >= self.pipeline.retries:
            return True
        return False

    __table_args__ = (
        Index('unique_run_in_progress', pipeline_id, target_time,
              postgresql_where=end_time==None, unique=True),
        # Can't have a ack time without targets, even if it's an empty list
        CheckConstraint('NOT (ack_time IS NOT NULL AND targets IS NULL)',
                        name='run_ack_without_targets_check'),
        # Can't have a end time without an ack time 
        CheckConstraint('NOT (end_time IS NOT NULL AND ack_time IS NULL)',
                        name='run_end_without_ack_check'),
    )


class Job(Base):
    __tablename__ = 'jobs'
    id = Column(Integer, primary_key=True)

    # These fields are populated when the job record is first created.
    pipeline_run_id = Column(Integer, ForeignKey('pipeline_runs.id'),
                             nullable=False)
    target = Column(Text, nullable=False)
    succeeded = Column(Boolean, nullable=False, default=False,
                       server_default=text('false'))
    retries_remaining = Column(Integer, nullable=False)
    created_time = Column(DateTime(timezone=True), nullable=False,
                  server_default=func.now())

    # These fields are populated when we receive an ack for the job from the ETL
    # service.
    start_time = Column(DateTime(timezone=True))
    hostname = Column(Text)
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
        CheckConstraint('NOT (start_time IS NOT NULL AND hostname IS NULL)',
                        name='job_start_without_hostname_check'),
        # Can't have a start time without a expire time
        CheckConstraint('NOT (start_time IS NOT NULL AND expires IS NULL)',
                        name='job_start_without_expire_check'),
    )


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
        Index('unique_log_line', 'job_id', 'line_num', unique=True),
    )


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
