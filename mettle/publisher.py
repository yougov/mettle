"""
This module will listen to the 'mettle_state' channel in Postgres, and
re-publish all messages to the 'mettle_state' exchange in RabbitMQ.

Messages will be UPDATE, INSERT, or DELETE events from the following tables:
- services
- pipelines
- pipeline_runs
- pipeline_runs_nacks
- jobs

"""
import json
import logging
import select

from functools32 import lru_cache
import pika
import pgpubsub
import psycopg2
from mettle_protocol import mq_escape

from mettle.settings import get_settings
from mettle.db import parse_pgurl

logger = logging.getLogger(__name__)
logger.setLevel(logging.INFO)
PIKA_PERSISTENT_MODE = 2
PG_CHANNEL = 'mettle_state'

def main():

    settings = get_settings()

    conn = psycopg2.connect(**parse_pgurl(settings.db_url))
    conn.set_isolation_level(psycopg2.extensions.ISOLATION_LEVEL_AUTOCOMMIT)

    rabbit_conn = pika.BlockingConnection(pika.URLParameters(settings.rabbit_url))
    rabbit = rabbit_conn.channel()
    exchange = settings['state_exchange']
    rabbit.exchange_declare(exchange=exchange, type='topic', durable=True)

    pubsub = pgpubsub.PubSub(conn)
    pubsub.listen(PG_CHANNEL)

    logger.info('Listening on Postgres channel "%s"' % PG_CHANNEL)

    for event in pubsub.events():
        payload = json.loads(event.payload)
        table = payload['tablename']

        with conn.cursor() as curs:
            # Handle payloads too big for a PG NOTIFY.
            if payload.get('error') == 'too long':
                payload = get_record_as_json(curs, table, payload['id'])

            # add service_name and pipeline_name where applicable, doing
            # another DB lookup if necessary.
            extra = extra_data(curs, table, payload['id'])
        payload.update(extra)
        publish_event(rabbit, exchange, payload)

def publish_event(chan, exchange, data):

    routing_key = data_to_routing_key(data)
    if len(routing_key) > 255:
        raise ValueError("Routing key longer than 255 bytes (%s)" %
                         routing_key)
    chan.basic_publish(
        exchange=exchange,
        routing_key=routing_key,
        body=json.dumps(data),
        properties=pika.BasicProperties(
            delivery_mode=PIKA_PERSISTENT_MODE,
        )
    )


def data_to_routing_key(data):
    data = dict(data)
    table = data['tablename']
    if 'target' in data and not data['target'] is None:
        data['target'] = mq_escape(data['target'])

    if table == 'services':
        return 'services.{name}'.format(**data)
    elif table == 'pipelines':
        return 'services.{service_name}.pipelines.{name}'.format(**data)
    elif table == 'pipeline_runs':
        return 'services.{service_name}.pipelines.{pipeline_name}.runs.{id}'.format(**data)
    elif table == 'pipeline_runs_nacks':
        return ('services.{service_name}'
                '.pipelines.{pipeline_name}'
                '.runs.{pipeline_run_id}'
                '.nacks.{id}').format(**data)
    elif table == 'jobs':
        rk = ('services.{service_name}'
                '.pipelines.{pipeline_name}'
                '.runs.{pipeline_run_id}'
                '.targets.{target}'
                '.jobs.{id}').format(**data)
        return rk
    elif table == 'notifications':
        routing_key = 'services.{service_name}'
        if data.get('pipeline_name'):
            routing_key += '.pipelines.{pipeline_name}'
            if data.get('pipeline_run_id'):
                routing_key += '.runs.{pipeline_run_id}'
                if data.get('job_id'):
                    routing_key += '.targets.{target}.jobs.{job_id}'
        return routing_key.format(**data) + '.notifications'
    else:
        raise ValueError('Unknown table: %s' % table)


def get_record_as_json(cur, tablename, row_id):
    """
    Get a single record from the database, by id, as json.
    """

    # IMPORTANT NOTE: Only use this function in trusted input.  Never on data
    # being created by users.  The table name is not escaped.
    q = """
    SELECT row_to_json(new_with_table)
    FROM (SELECT {t}.*, '{t}' AS tablename FROM {t}) new_with_table
    WHERE id=%s;""".format(
        t=tablename,
    )
    cur.execute(q, (row_id,))
    return cur.fetchone()[0]


# published rows from most tables won't include a 'service_name' or
# 'pipeline_name', but we want to include those as fields that consumers can
# use to filter their streams.  These lookup functions will get that extra data,
# with a cache so we don't have to do an extra DB read for every single write.

@lru_cache(maxsize=200)
def extra_data(cur, table, id):
    table_funcs = {
        'pipelines': extra_pipeline_data,
        'pipeline_runs': extra_pipeline_run_data,
        'pipeline_runs_nacks': extra_pipeline_run_nack_data,
        'jobs': extra_job_data,
        'notifications': extra_notification_data,
    }
    func = table_funcs.get(table, lambda x, y: {})
    return func(cur, id)

def extra_pipeline_data(cur, id):
    q = """
    SELECT services.name
    FROM pipelines
    JOIN services
        ON pipelines.service_id=services.id
    WHERE pipelines.id=%s;"""
    cur.execute(q, (id,))
    row = cur.fetchone()
    return {
        'service_name': row[0]
    }

def extra_pipeline_run_data(cur, id):
    q = """
    SELECT services.name, pipelines.name
    FROM pipeline_runs
    JOIN pipelines
        ON pipeline_runs.pipeline_id=pipelines.id
    JOIN services
        ON pipelines.service_id=services.id
    WHERE pipeline_runs.id=%s;"""
    cur.execute(q, (id,))
    row = cur.fetchone()
    return {
        'service_name': row[0],
        'pipeline_name': row[1],
    }

def extra_pipeline_run_nack_data(cur, id):
    q = """
    SELECT services.name, pipelines.name
    FROM pipeline_runs_nacks
    JOIN pipeline_runs
        ON pipeline_runs_nacks.pipeline_run_id=pipeline_runs.id
    JOIN pipelines
        ON pipeline_runs.pipeline_id=pipelines.id
    JOIN services
        ON pipelines.service_id=services.id
    WHERE pipeline_runs_nacks.id=%s;"""
    cur.execute(q, (id,))
    row = cur.fetchone()
    return {
        'service_name': row[0],
        'pipeline_name': row[1],
    }

def extra_job_data(cur, id):
    q = """
    SELECT services.name, pipelines.name
    FROM jobs
    JOIN pipeline_runs
        ON jobs.pipeline_run_id=pipeline_runs.id
    JOIN pipelines
        ON pipeline_runs.pipeline_id=pipelines.id
    JOIN services
        ON pipelines.service_id=services.id
    WHERE jobs.id=%s;"""
    cur.execute(q, (id,))
    row = cur.fetchone()
    return {
        'service_name': row[0],
        'pipeline_name': row[1],
    }

def extra_notification_data(cur, id):
    q_notification = """
    SELECT services.name, pipeline_id, job_id
    FROM notifications
    JOIN services
        ON notifications.service_id=services.id
    WHERE notifications.id=%s;"""
    cur.execute(q_notification, (id,))
    notification_row = cur.fetchone()
    service_name, pipeline_id, job_id = notification_row
    if pipeline_id is not None:
        q_pipeline = """
        SELECT name
        FROM pipelines
        WHERE id=%s;"""
        cur.execute(q_pipeline, (pipeline_id,))
        pipeline_name = cur.fetchone()[0]
    else:
        pipeline_name = None

    if job_id is not None:
        q_job = """
        SELECT target
        FROM jobs
        WHERE id=%s;"""
        cur.execute(q_job, (job_id,))
        target = cur.fetchone()[0]
    else:
        target = None

    return {
        'service_name': service_name,
        'pipeline_name': pipeline_name,
        'target': target,
    }
