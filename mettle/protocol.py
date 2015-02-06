import json

import pika

# This module provides functions and constants to implement the core protocol
# used by the timer, dispatcher, and ETL services.
ANNOUNCE_PIPELINE_RUN_EXCHANGE = 'mettle_announce_pipeline_run'
ACK_PIPELINE_RUN_EXCHANGE = 'mettle_ack_pipeline_run'
ANNOUNCE_JOB_EXCHANGE = 'mettle_announce_job'
ACK_JOB_EXCHANGE = 'mettle_ack_job'
JOB_LOGS_EXCHANGE = 'mettle_job_logs'

PIKA_PERSISTENT_MODE = 2

def announce_pipeline_run(pipeline_run, rabbit):

    pipeline = pipeline_run.pipeline
    service = pipeline.service
    routing_key = '.'.join([
        service.name,
        pipeline.name
    ])

    t = pipeline_run.target_time.isoformat()
    payload = {
        'pipeline': pipeline.name,
        'pipeline_run_id': pipeline_run.id,
        'service': service.name,
        'target_time': t,
    }

    print "Announcing pipeline run %s:%s:%s." % (service.name, pipeline.name, t)
    rabbit.exchange_declare(exchange=ANNOUNCE_PIPELINE_RUN_EXCHANGE,
                             type='topic', durable=True)
    rabbit.basic_publish(
        exchange=ANNOUNCE_PIPELINE_RUN_EXCHANGE,
        routing_key=routing_key,
        body=json.dumps(payload),
        properties=pika.BasicProperties(
            delivery_mode=PIKA_PERSISTENT_MODE
        )
    )
