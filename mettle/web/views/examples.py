from mettle.web.framework import View, Response
from mettle.web.rabbit import RabbitSocketView

class Index(View):
    def get(self):
        return Response('Hello World')


class Hello(View):
    def get(self, name):
        return Response('Hey there ' + name + '!')


class SleepyCounter(object):
    """
    An iterator that increments an integer once per second and yields a
    newline-terminated string
    """
    def __init__(self):
        self.num = 0

    def __iter__(self):
        return self

    def next(self):
        self.num += 1
        time.sleep(1)
        return '%s\n' % self.num


class Counter(View):
    """
    A long-lived stream of incrementing integers, one line per second.

    Best viewed with "curl -n localhost:8000/count/"

    Open up lots of terminals with that command to test how many simultaneous
    connections you can handle.
    """
    def get(self):
        return Response(SleepyCounter())


class SocketEcho(View):
    def websocket(self):
        message = self.ws.receive()
        self.ws.send(message)


class SocketCounter(View):
    def websocket(self):
        for line in SleepyCounter():
            self.ws.send(line)


class StreamMessages(RabbitSocketView):
    def websocket(self):
        bindings = [
            (mp.ANNOUNCE_PIPELINE_RUN_EXCHANGE, '#'),
            (mp.ACK_PIPELINE_RUN_EXCHANGE, '#'),
            (mp.CLAIM_JOB_EXCHANGE, '#'),
            (mp.END_JOB_EXCHANGE, '#'),
            (mp.JOB_LOGS_EXCHANGE, '#'),
        ]
        self.stream(bindings)
