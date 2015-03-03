# A dummy service that implements the mettle protocol for one pipeline, called
# "bar".  The "bar" pipeline will make targets of "tmp/<target_time>/[0-9].txt".

import os
import json
import socket
import time
import random
from datetime import timedelta

import pika
import isodate
import utc
import yaml

import mettle_protocol as mp


class BarPipeline(mp.Pipeline):

    def get_targets(self, target_time):
        # The get_targets function must return a dictionary where all the keys
        # are strings representing the targets to be created, and the values are
        # lists of targets on which a target depends.

        # In this example, we're making 11 targets.  Ten of them are just single
        # number strings, none of which has any dependencies.  The last one is
        # called 'manifest', and has a dependency on all the other ten.

        # Rules:
            # - all targets must be strings
            # - any dependency listed must itself be a target in the dict
            # - cyclic dependencies are not allowed
        return {
            '1': [],
            '2': [],
            '3': [],
            '4': [],
            '5': [],
            '6': [],
            '7': [],
            '8': [],
            '9': [],
            '10': [],
            'manifest': ['1', '2', '3', '4', '5', '6', '7', '8', '9', '10'],
        }

    def get_expire_time(self, target_time, target, start_time):
        """
        Given a target, and a UTC execution start time, return a UTC datetime
        for when the system should consider the job to have failed.
        """
        # Foo just hardcodes a 1 minute expiration time.
        return start_time + timedelta(minutes=1)

    def make_target(self, target_time, target):
        self.log("Making target %s." % target)
        try:
            if self._target_exists(target_time, target):
                self.log("%s already exists." % target)
            else:
                self.log("%s does not exist.  Creating." % target)

                # Let's just randomly fail 10% of the time.
                if random.random() < .2:
                    raise Exception("No one expects the Spanish Inquisition!")
                filename = self._target_to_filename(target_time, target)
                dirname = os.path.dirname(filename)
                if not os.path.isdir(dirname):
                    os.makedirs(dirname)
                with open(filename, 'w') as f:
                    if target.isdigit():
                        for x in xrange(int(target)):
                            f.write('%s\n' % x)
                            self.log('Wrote %s' % x)
                            time.sleep(1)
                    else:
                        f.write('all done!')
            return True
        except Exception as e:
            self.log("Error making target %s: %s" % (target, e))
            return False

    def _get_dir(self, target_time):
        return os.path.join('tmp', 'foo', target_time.isoformat())

    def _target_exists(self, target_time, target):
        filename = self._target_to_filename(target_time, target)
        if os.path.isfile(filename):
            return True

    def _target_to_filename(self, target_time, target):
        dirname = self._get_dir(target_time)
        return os.path.join(dirname, '%s.txt' % target)


def main():
    with open(os.environ['APP_SETTINGS_YAML'], 'rb') as f:
        settings = yaml.safe_load(f)
    rabbit_url = settings.get('rabbit_url',
                              'amqp://guest:guest@localhost:5672/%2f')
    pipelines = {
        'bar': BarPipeline,
    }
    mp.run_pipelines('foo', rabbit_url, pipelines)

if __name__ == '__main__':
    main()
