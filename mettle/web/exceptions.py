from collections import defaultdict

from spa import exceptions

# A mapping of exception class names that may be raised in handlers, and the
# corresponding HTTP error response classes that should be returned for them.

EXCEPTION_JSON_RESPONSES = defaultdict(lambda: exceptions.JSONInternalServerError)

EXCEPTION_JSON_RESPONSES.update({
    'sqlalchemy.exc.IntegrityError': exceptions.JSONConflict,
    'sqlalchemy.orm.exc.NoResultFound': exceptions.JSONNotFound,
})


def classpath(o):
    "Given a python object, return a string with its full class path"
    path = o.__class__.__name__
    if hasattr(o, 'module'):
        return o.__module__ + "." + path
    return path
