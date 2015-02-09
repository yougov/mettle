import os

import yaml

DEFAULTS = {
    'timer_sleep_secs': 5,
    'db_url': 'postgresql://postgres@/mettle',
    'rabbit_url': 'amqp://guest:guest@localhost:5672/%2f',

    # don't bother with pipeline runs older than this
    'lookback_days': 7,

    # delete logs older than this
    'max_log_days': 14,

    # new log messages within the last job_log_lookback_minutes will indicate
    # that a job is still alive and kicking, even if it's past its expiration
    # date.
    'job_log_lookback_minutes': 10,

    'web_worker_timeout': 30,
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
