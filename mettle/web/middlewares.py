

class DummyAuthMiddleware(object):

    def __init__(self, app, username):
        self.app = app
        self.username = username

    def __call__(self, environ, start_response):
        environ['beaker.session']['username'] = self.username
        return self.app(environ, start_response)
