
import os
import hashlib
from pkg_resources import resource_filename

from mettle.web.framework import View, Response

CSS_FILES = [
  'static/bower/pure/pure-min.css',
  'static/font/roboto/stylesheet.css',
  'static/css/mettle.css'
]

JS_FILES = [
  'static/bower/lodash/lodash.min.js',
  'static/bower/react/react.js',
  'static/bower/react-router/build/global/ReactRouter.min.js',
  'static/bower/graphlib/dist/graphlib.core.js',
  'static/bower/dagre/dist/dagre.core.min.js',
  'static/bower/reconnectingWebsocket/reconnecting-websocket.min.js',
  'static/bower/superagent/superagent.js'
]

TMPL = """
<html>
  <head>
    <title>Mettle</title>

    <!--style-->
    {css_files}
  </head>
  <body>
    <div id="content" class="pure-g"></div>

    <!--libraries-->
    {js_files}
  </body>
</html>
"""

DEV_SCRIPTS = """
<!--API interaction-->
<script src="/static/js/mettle.js" type="text/javascript"></script>

<!--UI-->
<script src="/static/bower/react/JSXTransformer.js" type="text/javascript" charset="utf-8" ></script>
<script src="/static/jsx/jobs.jsx" type="text/jsx"></script>
<script src="/static/jsx/targets.jsx" type="text/jsx"></script>
<script src="/static/jsx/runs.jsx" type="text/jsx"></script>
<script src="/static/jsx/pipelines.jsx" type="text/jsx"></script>
<script src="/static/jsx/services.jsx" type="text/jsx"></script>
<script src="/static/jsx/notifications.jsx" type="text/jsx"></script>
<script src="/static/jsx/app.jsx" type="text/jsx"></script>
"""

def hashfile(filename):
  filepath = resource_filename('mettle', filename)
  with open(filepath) as f:
    data = f.read()
  return hashlib.md5(data).hexdigest()[:8]

def generate_css_tag(filename):
  return '<link rel="stylesheet" href="/{filename}?{hash}" />'.format(filename=filename, hash=hashfile(filename))

def generate_js_tag(filename):
  return '<script src="/{filename}?{hash}" type="text/javascript"></script>'.format(filename=filename, hash=hashfile(filename))

if os.path.isfile(resource_filename('mettle', 'static/js/compiled.js')):
    JS_FILES.append('static/js/compiled.js')
    HOME = TMPL.format(js_files="\n".join(generate_js_tag(s) for s in JS_FILES),
                       css_files="\n".join(generate_css_tag(s) for s in CSS_FILES))
else:
    HOME = TMPL.format(js_files="\n".join(generate_js_tag(s) for s in JS_FILES)+DEV_SCRIPTS,
                       css_files="\n".join(generate_css_tag(s) for s in CSS_FILES))


class Index(View):
    def get(self):
        return Response(HOME, content_type='text/html')
