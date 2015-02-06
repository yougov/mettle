from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.schema import Index, UniqueConstraint
from sqlalchemy.dialects.postgresql import (ARRAY, JSON)
from sqlalchemy import (Column, Integer, Text, ForeignKey, DateTime, Boolean,
                        func, CheckConstraint)
from sqlalchemy.ext.mutable import MutableDict


Base = declarative_base()


class Service(Base):
    __tablename__ = 'services'
    id = Column(Integer, primary_key=True)
    name = Column(Text, nullable=False)
    broker = Column(Text, nullable=False)
    description = Column(Text)
    updated_by = Column(Text, nullable=False)

    __table_args__ = (
        UniqueConstraint('name'),
    )


class NotificationList(Base):
    __tablename__ = 'notification_lists'
    id = Column(Integer, primary_key=True)
    name = Column(Text, nullable=False)
    recipients = Column(ARRAY(Text), nullable=False)
    updated_by = Column(Text, nullable=False)


class Pipeline(Base):
    __tablename__ = 'pipelines'
    id = Column(Integer, primary_key=True)
    name = Column(Text, nullable=False)
    service_id = Column(Integer, ForeignKey('services.id'), nullable=False)
    schedule = Column(MutableDict.as_mutable(JSON), default={})
    notification_list_id = Column(Integer, ForeignKey('notification_lists.id'),
                                  nullable=False)
    updated_by = Column(Text, nullable=False)
    __table_args__ = (
        UniqueConstraint('name', 'service_id'),
    )


class PipelineRun(Base):
    __tablename__ = 'pipeline_runs'
    id = Column(Integer, primary_key=True)
    pipeline_id = Column(Integer, ForeignKey('pipelines.id'), nullable=False)
    created_time = Column(DateTime(timezone=True), nullable=False,
                  server_default=func.now())
    target_time = Column(DateTime(timezone=True), nullable=False)
    ack_time = Column(DateTime(timezone=True))
    started_by = Column(Text, nullable=False)


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
    expires = Column

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


# TODO: Add a trigger to changes on Service, NotificationList, and Pipeline, to
# record all changes in this table.
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
