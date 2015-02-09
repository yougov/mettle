# A dummy service that implements the mettle protocol for one pipeline, called
# "bar".  The "bar" pipeline will make targets of "tmp/<target_time>/[0-9].txt".

import os
import json
import socket
import time
from datetime import timedelta

import pika
import isodate
import utc

from mettle_protocol.settings import get_settings
import mettle_protocol as mp


class BarPipeline(mp.Pipeline):

    def get_targets(self, target_time):
        dirname = self._get_dir(target_time)
        targets = [str(x) for x in xrange(1, 11)]
        present = []
        absent = []
        for t in targets:
            if self._target_exists(target_time, t):
                present.append(t)
            else:
                absent.append(t)
        return {
            'present': present,
            'absent': absent,
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
                filename = self._target_to_filename(target_time, target)
                dirname = os.path.dirname(filename)
                if not os.path.isdir(dirname):
                    os.makedirs(dirname)
                with open(filename, 'w') as f:
                    # This pipeline just uses a simple int as the target.
                    for x in xrange(int(target)):
                        f.write('%s\n' % x)
                        self.log('Wrote %s' % x)
                        time.sleep(1)
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
    settings = get_settings()
    pipelines = {
        'bar': BarPipeline,
    }
    mp.run_pipelines('foo', settings.rabbit_url, pipelines)

if __name__ == '__main__':
    main()
