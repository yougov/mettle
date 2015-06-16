import logging
import argparse

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


def run_web():
    from mettle.web.green import patch
    patch()
    import spa
    from mettle.web import app
    spa.run(app)


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
