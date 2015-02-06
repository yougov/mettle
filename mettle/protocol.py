import json

# This module provides functions and constants to implement the core protocol
# used by the timer, dispatcher, and ETL services.
ANNOUNCE_PIPELINE_RUN_EXCHANGE = 'mettle_announce_pipeline_run'
ACK_PIPELINE_RUN_EXCHANGE = 'mettle_ack_pipeline_run'
ANNOUNCE_JOB_EXCHANGE = 'mettle_announce_job'
ACK_JOB_EXCHANGE = 'mettle_ack_job'
JOB_LOGS_EXCHANGE = 'mettle_job_logs'


def announce_pipeline_run(pipeline_run, rabbit):

    pipeline = pipeline_run.pipeline
    service = pipeline.service
    routing_key = '.'.join([
        service.name,
        pipeline.name

    ])

    payload = {
        'pipeline': pipeline.name,
        'pipeline_run_id': pipeline_run.id,
        'service': service.name,
        'target_time': pipeline_run.target_time.isoformat(),
    }

    print json.dumps(payload)
