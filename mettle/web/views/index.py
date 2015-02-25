import pkg_resources

from mettle.web.framework import View, Response


class Index(View):
    def get(self):
        fname = pkg_resources.resource_filename('mettle', 'static/index.html')
        f = open(fname)
        return Response(f, direct_passthrough=True, content_type='text/html')
