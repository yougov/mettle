from spa import Request

class MettleRequest(Request):
    def __init__(self, environ, *args, **kwargs):
        super(MettleRequest, self).__init__(environ, *args, **kwargs)
        # Assume that the environ has a 'mettle_session' key.  Tack that on to
        # the request.
        self.session = environ['beaker.session']
