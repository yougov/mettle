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
import psycopg2
from mettle_protocol import mq_escape

from mettle.settings import get_settings
from mettle.db import parse_pgurl

logger = logging.getLogger(__name__)
logger.setLevel(logging.INFO)
PIKA_PERSISTENT_MODE = 2

def main():

    settings = get_settings()
    conn = psycopg2.connect(**parse_pgurl(settings.db_url))
    conn.set_isolation_level(psycopg2.extensions.ISOLATION_LEVEL_AUTOCOMMIT)

    pg_listen_channel = 'mettle_state'

    rabbit_conn = pika.BlockingConnection(pika.URLParameters(settings.rabbit_url))
    rabbit = rabbit_conn.channel()
    exchange = settings['state_exchange']
    rabbit.exchange_declare(exchange=exchange, type='topic', durable=True)

    with conn.cursor() as curs:
        logger.info("Listening for notifications to %s." % pg_listen_channel)
        curs.execute('LISTEN %s;' % pg_listen_channel)
        while True:
            if select.select([conn], [], [], 5) == ([], [], []):
                logger.debug("No messages for 5 seconds.")
            else:
                conn.poll()
                while conn.notifies:
                    notify = conn.notifies.pop()
                    payload = json.loads(notify.payload)
                    table = payload['tablename']

                    # Handle payloads too big for a PG NOTIFY.
                    if payload.get('error') == 'too long':
                        payload = get_record_as_json(curs, table, payload['id'])

                    # add service_name and pipeline_name where applicable, doing
                    # another DB lookup if necessary.
                    extra = extra_data(curs, table, payload['id'])
                    payload.update(extra)

                    rabbit.basic_publish(
                        exchange=exchange,
                        routing_key=data_to_routing_key(payload),
                        body=json.dumps(payload),
                        properties=pika.BasicProperties(
                            delivery_mode=PIKA_PERSISTENT_MODE,
                        )
                    )

def data_to_routing_key(data):
    table = data['tablename']
    if table == 'services':
        return data['name']
    elif table == 'pipelines':
        return '{service_name}.{name}'.format(**data)
    elif table == 'pipeline_runs':
        return '{service_name}.{pipeline_name}.{id}'.format(**data)
    elif table == 'pipeline_runs_nacks':
        return '{service_name}.{pipeline_name}.{pipeline_run_id}.nacks.{id}'.format(**data)
    elif table == 'jobs':
        data['target'] = mq_escape(data['target'])
        return '{service_name}.{pipeline_name}.{pipeline_run_id}.jobs.{target}.{id}'.format(**data)
    else:
        raise ValueError('Unknown table: %s' % table)


def get_record_as_json(cur, tablename, row_id):
    """
    Get a single record from the database, by id, as json.
    """

    # IMPORTANT NOTE: Only use this function in trusted input.  Never on data
    # being created by users.  The table name is not escaped.
    q = """
    SELECT row_to_json(new_with_table)::text
    FROM (SELECT {t}.*, '{t}' as tablename) new_with_table
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