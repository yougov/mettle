import os
from pkg_resources import resource_filename

from spa import Handler, Response
from spa.static.hashed import get_hash, add_hash_to_filepath

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

JS_PROD = [
    'static/js/compiled.js',
]

JS_DEV = [
    'static/js/mettle.js',
    'static/bower/react/JSXTransformer.js',
    'static/jsx/jobs.jsx',
    'static/jsx/targets.jsx',
    'static/jsx/runs.jsx',
    'static/jsx/pipelines.jsx',
    'static/jsx/services.jsx',
    'static/jsx/notifications.jsx',
    'static/jsx/app.jsx',
]


def hashfile(filename):
  filepath = resource_filename('mettle', filename)
  with open(filepath) as f:
    return get_hash(f)

def css_tag(path):
    return '<link rel="stylesheet" href="/{path}" />'.format(path=path)

def js_tag(path):
    mime = 'text/jsx' if path.endswith('jsx') else 'text/javascript'
    return '<script src="/{path}" type="{mime}"></script>'.format(path=path,
                                                                  mime=mime)

def render_homepage(hashing_enabled):
    if hashing_enabled:
        js_files = [add_hash_to_filepath(l, hashfile(l)) for l in JS_FILES]
        js_files += [add_hash_to_filepath(l, hashfile(l)) for l in JS_PROD]
        css_files = [add_hash_to_filepath(l, hashfile(l)) for l in CSS_FILES]
    else:
        js_files = JS_FILES + JS_DEV
        css_files = CSS_FILES

    js = '\n'.join([js_tag(j) for j in js_files])
    css = '\n'.join([css_tag(c) for c in css_files])
    rendered = TMPL.format(js_files=js, css_files=css)
    return rendered

cache = {}

class Index(Handler):

    def __init__(self, app, *args, **kwargs):
        self.settings = app.settings
        super(Index, self).__init__(app, *args, **kwargs)

    def get(self):
        if 'home' not in cache:
            cache['home'] = render_homepage(self.settings.enable_static_hashing)
        return Response(cache['home'], content_type='text/html')
