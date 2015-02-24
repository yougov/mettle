import json
import logging
import textwrap

import pika
from sqlalchemy.exc import IntegrityError

from mettle.settings import get_settings
from mettle.models import JobLogLine
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
    rabbit.queue_declare(queue=queue_name, exclusive=False,
                         durable=True)
    rabbit.queue_bind(exchange=mp.JOB_LOGS_EXCHANGE,
                      queue=queue_name, routing_key='#')
    logger.info('Bound exchange %s to queue %s' % (mp.JOB_LOGS_EXCHANGE,
                                                   queue_name))

    Session = make_session_cls(settings.db_url)
    for method, properties, body in rabbit.consume(queue=queue_name):
        db = Session()
        data = json.loads(body)
        job_id = data['job_id']
        line_num = data['line_num']
        message = data['msg']
        try:
            db.add(JobLogLine(
                job_id=job_id,
                line_num=line_num,
                message=message,
            ))
            db.commit()
            logger.info(message)
        except IntegrityError:
            # We probably got a duplicate log line, which can happen given
            # Rabbit retries.  Query DB for log line matching job_id and
            # line_num.  If we have one, and it is the same message, then just
            # carry on.  If the message is different, then log an error.
            db.rollback()
            existing_line = db.query(JobLogLine).filter_by(job_id=job_id,
                                                           line_num=line_num).one()
            if existing_line.message != message:
                err = """Job {job_id}, log line {num} is stored as
                this:\n{old}\n\n but the queue has just produced a new message
                for the same line, with this value:\n{new}"""


                logger.error(textwrap.dedent(err).format(
                    job_id=job_id,
                    num=line_num,
                    old=existing_line.message,
                    new=message,
                ))

        rabbit.basic_ack(method.delivery_tag)

if __name__ == '__main__':
    main()
