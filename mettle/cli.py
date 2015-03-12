import logging
import argparse
import os

from gunicorn.app.base import Application
from gunicorn import util
from mettle.settings import get_settings
from mettle import migrations


logging.basicConfig()

def main():
    parser = argparse.ArgumentParser()

    commands = {
        'dispatcher': run_dispatcher,
        'logcollector': run_logcollector,
        'migrate': migrations.run,
        'migrate_and_sleep': migrations.run_and_sleep,
        'timer': run_timer,
        'publisher': run_publisher,
        'web': run_web,
    }

    cmd_help = "one of: %s" % ', '.join(sorted(commands.keys()))

    parser.add_argument('command', help=cmd_help, type=lambda x: commands.get(x))

    args = parser.parse_args()

    if args.command is None:
        raise SystemExit('Command must be ' + cmd_help)
    args.command()


class MettleApplication(Application):
    """
    Wrapper around gunicorn so we can start app as "mettle web" instead of a
    big ugly gunicorn line.
    """

    def __init__(self, settings):
        self.settings = settings
        super(MettleApplication, self).__init__()

    def init(self, *args):
        """
        Return mettle-specific settings.
        """
        return {
            'bind': '0.0.0.0:%s' % os.getenv('PORT', 8000),
            'worker_class': 'geventwebsocket.gunicorn.workers.GeventWebSocketWorker',
            'timeout': self.settings.web_worker_timeout,
            'accesslog': '-',
        }

    def load(self):
        return util.import_app("mettle.web:app")

def run_web():
    from mettle.web.green import patch
    patch()
    MettleApplication(get_settings()).run()


def run_dispatcher():
    from mettle import dispatcher
    dispatcher.main()


def run_timer():
    from mettle import timer
    timer.main()


def run_logcollector():
    from mettle import logcollector
    logcollector.main()


def run_publisher():
    from mettle import publisher
    publisher.main()
