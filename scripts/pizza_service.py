# A dummy service that implements the mettle protocol for one pipeline, called
# "bar".  The "bar" pipeline will make targets of "tmp/<target_time>/[0-9].txt".

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


class PizzaPipeline(mp.Pipeline):

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

                # Let's just randomly fail 10% of the time.
                if random.random() < .1:
                    raise Exception("No one expects the Spanish Inquisition!")
                filename = self._target_to_filename(target_time, target)
                dirname = os.path.dirname(filename)
                if not os.path.isdir(dirname):
                    os.makedirs(dirname)
                with open(filename, 'w') as f:
                    # sleep some random amount of time from 1 to 5 seconds.
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


class PepperoniPipeline(PizzaPipeline):

    targets = {
            "flour": [],
            "water": [],
            "yeast": [],
            "sugar": [],
            "salt": [],
            "olive oil": [],
            "mix": ["flour", "water", "yeast", "sugar", "salt", "olive oil"],
            "raise": ["mix"],
            "roll": ["raise"],
            "sauce": ["roll"],
            "cheese": ["sauce"],
            "pepperoni": ["cheese"],
            "green peppers": ["cheese"],
            "mushrooms": ["cheese"],
            "bake": ["pepperoni", "green peppers", "mushrooms"],
            "box": ["bake"],
            "deliver": ["box"],
            "eat": ["deliver"]
        }

    def get_targets(self, target_time):
        # The get_targets function must return a dictionary where all the keys
        # are strings representing the targets to be created, and the values are
        # lists of targets on which a target depends.

        # Rules:
            # - all targets must be strings
            # - any dependency listed must itself be a target in the dict
            # - cyclic dependencies are not allowed
        return self.targets

    def get_target_parameters(self, target_time):
        return {
            "flour": {"foo": "bar"},
        }


class HawaiianPipeline(PizzaPipeline):
    def get_targets(self, target_time):
        # The HawaiianPipeline is in no hurry.  If you call get_targets with a
        # target_time that's too recent, it will nack and make you wait.
        now = utc.now()
        wait_until = target_time + timedelta(days=4)

        if now < wait_until:
            raise mp.PipelineNack("What's the rush, man?", wait_until)

        return {
            "flour": [],
            "water": [],
            "yeast": [],
            "sugar": [],
            "salt": [],
            "olive oil": [],
            "mix": ["flour", "water", "yeast", "sugar", "salt", "olive oil"],
            "raise": ["mix"],
            "roll": ["raise"],
            "sauce": ["roll"],
            "cheese": ["sauce"],
            "ham": ["cheese"],
            "pineapple": ["cheese"],
            "bake": ["ham", "pineapple"],
            "box": ["bake"],
            "deliver": ["box"],
            "eat": ["deliver"]
        }


def _get_queue_name(service_name):
    # Helper function specifically for this demo script.  You probably don't
    # need one of these in your own services
    try:
        return sys.argv[1]
    except IndexError:
        return mp.service_queue_name(service_name)


def main():
    with open(os.environ['APP_SETTINGS_YAML'], 'rb') as f:
        settings = yaml.safe_load(f)
    rabbit_url = settings.get('rabbit_url',
                              'amqp://guest:guest@127.0.0.1:5672/%2f')
    pipelines = {
        'pepperoni': PepperoniPipeline,
        'hawaiian': HawaiianPipeline,
    }
    service_name = 'pizza'
    mp.run_pipelines(service_name, rabbit_url, pipelines,
                     _get_queue_name(service_name))

if __name__ == '__main__':
    main()
