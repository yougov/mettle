import logging
import select

import psycopg2

from mettle.settings import get_settings
from mettle.web.framework import View
from mettle.db import parse_pgurl

logger = logging.getLogger(__name__)
logger.setLevel(logging.INFO)


class StateStream(View):
    def websocket(self):
        settings = get_settings()
        # connect to postgres
        # listen on mettle_state channel.  send every message on through the
        # websocket.
        conn = psycopg2.connect(**parse_pgurl(settings.db_url))
        conn.set_isolation_level(psycopg2.extensions.ISOLATION_LEVEL_AUTOCOMMIT)

        listen_channel = 'mettle_state'

        with conn.cursor() as curs:
            logger.info("Listening for notifications to %s." % listen_channel)
            curs.execute('LISTEN %s;' % listen_channel)
            while True:
                if select.select([conn], [], [], 5) == ([], [], []):
                    logger.debug("No messages for 5 seconds.")
                else:
                    conn.poll()
                    while conn.notifies:
                        notify = conn.notifies.pop()
                        self.ws.send(notify.payload)
