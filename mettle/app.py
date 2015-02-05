from gevent.monkey import patch_all; patch_all()
from gevent import pywsgi

from webzeug import App, Request, Response, View
import time


class Index(View):
    def GET(self):
        return Response('Hello World')


class Hello(View):
    def GET(self, name):
        return Response('Hey there ' + name + '!')


class CountIter(object):
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
    def GET(self):
        return Response(CountIter())


app = App([
    ('/', 'index', Index),
    ('/people/<name>/', 'hello', Hello),
    ('/count/', 'count', Counter),
])


if __name__ == "__main__":
    server = pywsgi.WSGIServer(('', 8000), app)
    server.serve_forever()
