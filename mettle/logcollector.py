import json
import logging

import pika

from mettle.settings import get_settings
from mettle.models import JobLogLine
from mettle.lock import lock_and_announce_job
from mettle.db import make_session_cls
import mettle_protocol as mp

logger = logging.getLogger(__name__)
logger.setLevel(logging.INFO)

def main():
    settings = get_settings()

    rabbit_conn = pika.BlockingConnection(pika.URLParameters(settings.rabbit_url))
    rabbit = rabbit_conn.channel()
    mp.declare_exchanges(rabbit)
    queue_name = 'mettle_job_logs'
    queue = rabbit.queue_declare(queue=queue_name, exclusive=False,
                                 durable=True)
    rabbit.queue_bind(exchange=mp.JOB_LOGS_EXCHANGE,
                      queue=queue_name, routing_key='#')
    logger.info('Bound exchange %s to queue %s' % (mp.JOB_LOGS_EXCHANGE,
                                                   queue_name))

    Session = make_session_cls(settings.db_url)
    for method, properties, body in rabbit.consume(queue=queue_name):
        db = Session()
        data = json.loads(body)
        db.add(JobLogLine(
            job_id=data['job_id'],
            line_num=data['line_num'],
            message=data['msg'],
        ))
        logger.info(data['msg'])
        db.commit()
        rabbit.basic_ack(method.delivery_tag)

if __name__ == '__main__':
    main()
