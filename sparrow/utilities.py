# -*- coding: utf-8 -*-
import email.utils
import time
from exceptions import SparrowException, HTTPError, BreakTheSparrow
from response import response
import mimetypes

def abort(code=500, text='Unknown Error: Appliction stopped.'):
    """ Aborts execution and causes a HTTP error. """
    raise HTTPError(code, text)


def redirect(url, code=307):
    """ Aborts execution and causes a 307 redirect """
    response.status = code
    response.header['Location'] = url
    raise BreakTheSparrow("")

def send_file(filename, root, guessmime = True, mimetype = None):
    """ Aborts execution and sends a static files as response. """
    root = os.path.abspath(root) + os.sep
    filename = os.path.abspath(os.path.join(root, filename.strip('/\\')))

    if not filename.startswith(root):
        abort(401, "Access denied.")
    if not os.path.exists(filename) or not os.path.isfile(filename):
        abort(404, "File does not exist.")
    if not os.access(filename, os.R_OK):
        abort(401, "You do not have permission to access this file.")

    if guessmime and not mimetype:
        mimetype = mimetypes.guess_type(filename)[0]
    if not mimetype: mimetype = 'text/plain'
    response.content_type = mimetype

    stats = os.stat(filename)
    if 'Last-Modified' not in response.header:
        lm = time.strftime("%a, %d %b %Y %H:%M:%S GMT", time.gmtime(stats.st_mtime))
        response.header['Last-Modified'] = lm
    if 'HTTP_IF_MODIFIED_SINCE' in request.environ:
        ims = request.environ['HTTP_IF_MODIFIED_SINCE']
        # IE sends "<date>; length=146"
        ims = ims.split(";")[0].strip()
        ims = parse_date(ims)
        if ims is not None and ims >= stats.st_mtime:
           abort(304, "Not modified")
    if 'Content-Length' not in response.header:
        response.header['Content-Length'] = str(stats.st_size)
    raise BreakTheSparrow(open(filename, 'rb'))

def parse_date(ims):
    """
    ims: date strings usually found in HTTP header.
    returns UTC epoch.
    """
    try:
        ts = email.utils.parsedate_tz(ims)
        if ts is not None:
            if ts[9] is None:
                return time.mktime(ts[:8] + (0,)) - time.timezone
            else:
                return time.mktime(ts[:8] + (0,)) - ts[9] - time.timezone
    except (ValueError, IndexError):
        return None

def validate(**vkargs):
    """
    Validates and manipulates keyword arguments by user defined callables. 
    Handles ValueError and missing arguments by raising HTTPError(403).
    """
    def decorator(func):
        def wrapper(**kargs):
            for key, value in vkargs.iteritems():
                if key not in kargs:
                    abort(403, 'Missing parameter: %s' % key)
                try:
                    kargs[key] = value(kargs[key])
                except ValueError as e:
                    abort(403, 'Wrong parameter format for: %s (error %s)' % (key, str(e)))
            return func(**kargs)
        return wrapper
    return decorator
