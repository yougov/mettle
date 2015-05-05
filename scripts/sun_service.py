"""
This dummy service exists to demonstrate chaining between pipelines.

You can run this service and test chaining by putting settings like this in
your settings file and running the datastub proc.

stub_services:
  sun:
    pipeline_names: [sunrise, sunset]
stub_pipelines:
- name: sunrise
  crontab: "0 6 * * *"
  service: sun
  notification_list: devs
- name: sunset
  chained_from: sunrise
  service: sun
  notification_list: devs
"""

import os
import json
import socket
import time
import random
import sys
from datetime import timedelta

import pika
import isodate
import utc
import yaml

import mettle_protocol as mp


class SunPipeline(mp.Pipeline):

    def get_expire_time(self, target_time, target, start_time):
        """
        Given a target, and a UTC execution start time, return a UTC datetime
        for when the system should consider the job to have failed.
        """
        # We just hardcode a 1 minute expiration time.
        return start_time + timedelta(minutes=1)

    def make_target(self, target_time, target, target_parameters):
        self.log("Making target %s." % target)
        try:
            if self._target_exists(target_time, target):
                self.log("%s already exists." % target)
            else:
                self.log("%s does not exist.  Creating." % target)

                filename = self._target_to_filename(target_time, target)
                dirname = os.path.dirname(filename)
                if not os.path.isdir(dirname):
                    os.makedirs(dirname)
                with open(filename, 'w') as f:
                    time.sleep(random.randint(1, 5))
                    f.write(target)
            return True
        except Exception as e:
            self.log("Error making target %s: %s" % (target, e))
            return False

    def _get_dir(self, target_time):
        return os.path.join('tmp', type(self).__name__, target_time.isoformat())

    def _target_exists(self, target_time, target):
        filename = self._target_to_filename(target_time, target)
        if os.path.isfile(filename):
            return True

    def _target_to_filename(self, target_time, target):
        dirname = self._get_dir(target_time)
        return os.path.join(dirname, '%s.txt' % target)


class SunrisePipeline(SunPipeline):
    def get_targets(self, target_time):
        return {
            "sunrise": [],
        }


class SunsetPipeline(SunPipeline):
    def get_targets(self, target_time):
        return {
            "sunset": [],
        }


def main():
    with open(os.environ['APP_SETTINGS_YAML'], 'rb') as f:
        settings = yaml.safe_load(f)
    rabbit_url = settings.get('rabbit_url',
                              'amqp://guest:guest@127.0.0.1:5672/%2f')
    pipelines = {
        'sunrise': SunrisePipeline,
        'sunset': SunsetPipeline,
    }
    service_name = 'sun'
    mp.run_pipelines(service_name, rabbit_url, pipelines)

if __name__ == '__main__':
    main()
