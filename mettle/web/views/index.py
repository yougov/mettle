
import os
from pkg_resources import resource_filename

from mettle.web.framework import View, Response

with open(resource_filename('mettle', 'static/index.html')) as f:
    TMPL = f.read()

if os.path.isfile(resource_filename('mettle', 'static/js/compiled.js')):
    SCRIPTS_FILE = resource_filename('mettle', 'static/_prod_scripts.html')
else:
    SCRIPTS_FILE = resource_filename('mettle', 'static/_dev_scripts.html')

with open(SCRIPTS_FILE) as f:
    HOME = TMPL.format(scripts=f.read())


class Index(View):
    def get(self):
        return Response(HOME, content_type='text/html')
