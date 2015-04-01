import os

import yaml

DEFAULTS = {
    'db_url': 'postgresql://postgres@/mettle',

    # new log messages within the last job_log_lookback_minutes will indicate
    # that a job is still alive and kicking, even if it's past its expiration
    # date.
    'job_log_lookback_minutes': 10,

    # don't bother with pipeline runs older than this
    'lookback_days': 7,

    # delete logs older than this
    'max_log_days': 14,

    'rabbit_url': 'amqp://guest:guest@localhost:5672/%2f',

    # To enable sending of notification emails on pipeline failures, set this to
    # a host:port string like "mymailserver.com:25"
    'smtp_url': None,
    'smtp_sender': ['Mettle Server', 'mettle@example.com'],

    # The RabbitMQ exchange where updates to Postgres tables are published.
    'state_exchange': 'mettle_state',

    'timer_sleep_secs': 60,
    'web_worker_timeout': 30,
    'websocket_ping_interval': 1,
}


class AttrDict(dict):
    def __init__(self, *args, **kwargs):
        super(AttrDict, self).__init__(*args, **kwargs)
        self.__dict__ = self


def get_settings():
    settings = AttrDict()
    settings.update(DEFAULTS)
    if 'APP_SETTINGS_YAML' in os.environ:
        with open(os.environ['APP_SETTINGS_YAML']) as f:
            settings.update(yaml.safe_load(f.read()))
    return settings
