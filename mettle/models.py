from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.schema import Index, UniqueConstraint
from sqlalchemy.dialects.postgresql import (ARRAY, JSON)
from sqlalchemy import (Column, Integer, Text, ForeignKey, DateTime, Boolean,
                        func, CheckConstraint)
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
    created_time = Column(DateTime(timezone=True), nullable=False,
                  server_default=func.now())
    target_time = Column(DateTime(timezone=True), nullable=False)
    ack_time = Column(DateTime(timezone=True))

    # We'll periodically check to see if each target in the pipeline run has a
    # successfully completed job.  Once they all do, we can set the end_time for
    # this run.  That will stop the timer proc from announcing the run anymore.
    targets = Column(ARRAY(Text), default=[])
    end_time = Column(DateTime(timezone=True))

    # either 'timer', or name of the user who manually started the pipeline run.
    started_by = Column(Text, nullable=False)

    pipeline = relationship("Pipeline", backref=backref('pipeline_runs',
                                                        order_by=created_time))


class Job(Base):
    __tablename__ = 'jobs'
    id = Column(Integer, primary_key=True)
    pipeline_run_id = Column(Integer, ForeignKey('pipeline_runs.id'),
                             nullable=False)
    target = Column(Text, nullable=False)

    in_progress = Column(Boolean, nullable=False)

    STATUS_NEW = 0
    STATUS_STARTED = 1
    STATUS_SUCCEEDED = 2
    STATUS_FAILED = 3

    STATUS_LABELS = {
        STATUS_NEW: 'New',
        STATUS_STARTED: 'Started',
        STATUS_SUCCEEDED: 'Succeeded',
        STATUS_FAILED: 'Failed',
    }

    status = Column(Integer, nullable=False)
    hostname = Column(Text)
    expires = Column(DateTime(timezone=True))
    retries_remaining = Column(Integer, nullable=False)

    # The time that the dispatcher created this job record
    created_time = Column(DateTime(timezone=True), nullable=False,
                  server_default=func.now())

    # The time reported by the ETL service that the job started
    start_time = Column(DateTime(timezone=True), nullable=False)

    # The time reported by the ETL service that the job ended (whether in
    # success or failure)
    end_time = Column(DateTime(timezone=True), nullable=False)

    __table_args__ = (
        CheckConstraint("status in (0, 1, 2, 3)", name="job_status_check"),
    )
Index('unique_target_in_progress', Job.target, postgresql_where=Job.in_progress,
     unique=True)


class JobLogLine(Base):
    __tablename__ = 'job_log_lines'
    id = Column(Integer, primary_key=True)
    job_id = Column(Integer, ForeignKey('jobs.id'), nullable=False)
    message = Column(Text, nullable=False)
    line_num = Column(Integer, nullable=False)
    received_time = Column(DateTime(timezone=True), nullable=False,
                           server_default=func.now())

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
