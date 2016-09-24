# -*- coding: utf-8 -*-

import re
import traceback
from common import TRACEBACK_TEMPLATE, HTTP_CODES
from request import request as request_thread_local
from response import response as response_thread_local
from sparrow_exceptions import HTTPError, BreakTheSparrow
import json
json_dumps = json.dumps
import types

class Sparrow(object):

    def __init__(self, catchall=True, optimize=False, autojson=True):
        self.simple_routes = {}
        self.regexp_routes = {}
        self.default_route = None
        self.error_handler = {}
        self.optimize = optimize
        self.autojson = autojson
        self.catchall = catchall
        self.serve = True

    def match_url(self, url, method='GET'):
        """
        Returns the first matching handler and a parameter dict or (None, None)
        """
        url = url.strip().lstrip("/ ")
        # Search for static routes first
        route = self.simple_routes.get(method,{}).get(url,None)
        if route:
            return (route, {})
        
        routes = self.regexp_routes.get(method,[])
        for i in range(len(routes)):
            match = routes[i][0].match(url)
            if match:
                handler = routes[i][1]
                if i > 0 and self.optimize and random.random() <= 0.001:
                    routes[i-1], routes[i] = routes[i], routes[i-1]
                return (handler, match.groupdict())
        if self.default_route:
            return (self.default_route, {})
        if method == 'HEAD': # Fall back to GET
            return self.match_url(url)
        else:
            return (None, None)

    def add_route(self, route, handler, method='GET', **kargs):
        """ Adds a new route to the route mappings. """
        method = method.strip().upper()
        route = route.strip().lstrip('$^/ ').rstrip('$^ ')
        if re.match(r'^(\w+/)*\w*$', route):
            self.simple_routes.setdefault(method, {})[route] = handler
        else:
            route = re.sub(r':([a-zA-Z_]+)(?P<uniq>[^\w/])(?P<re>.+?)(?P=uniq)',
                           r'(?P<\1>\g<re>)',route) # \1表示的是第一个匹配到的括号内内容
                                                    # \g<re> 表示的是(?<re>.+?)中的内容
                                                    # 其中,+?表示非贪婪匹配
            route = re.sub(r':([a-zA-Z_]+)', r'(?P<\1>[^/]+)', route)
            route = re.compile('^%s$' % route)
            self.regexp_routes.setdefault(method, []).append([route, handler])

    def route(self, url, **kargs):
        """
        Decorator for request handler.
        Same as add_route(url, handler, **kargs).
        """
        def wrapper(handler):
            self.add_route(url, handler, **kargs)
            return handler
        return wrapper

    def set_default(self, handler):
        self.default_route = handler

    def default(self):
        """ Decorator for request handler. Same as add_defroute( handler )."""
        def wrapper(handler):
            self.set_default(handler)
            return handler
        return wrapper

    def set_error_handler(self, code, handler):
        """ Adds a new error handler. """
        self.error_handler[int(code)] = handler

    def error(self, code=500):
        """
        Decorator for error handler.
        Same as set_error_handler(code, handler).
        """
        def wrapper(handler):
            self.set_error_handler(code, handler)
            return handler
        return wrapper

    def cast(self, out):
        """
        Cast the output to an iterable of strings.
        Set Content-Type and Content-Length when possible. Then clear output
        on HEAD requests.
        Supports: False, str, unicode, list(unicode), dict(), open()
        """
        if self.autojson and json_dumps and isinstance(out, dict):
            out = [json_dumps(out)]
            response_thread_local.content_type = 'application/json'
        elif not out:
            out = []
            response_thread_local.header['Content-Length'] = '0'
        elif isinstance(out, types.StringType):
            out = [out]
        elif isinstance(out, unicode):
            out = [out.encode(response_thread_local.charset)]
        elif isinstance(out, list) and isinstance(out[0], unicode):
            out = map(lambda x: x.encode(response_thread_local.charset), out)
        elif hasattr(out, 'read'):
            out = request_thread_local.environ.get('wsgi.file_wrapper', lambda x: iter(lambda: x.read(8192), ''))(out)
        if isinstance(out, list) and len(out) == 1:
            response_thread_local.header['Content-Length'] = str(len(out[0]))
        if not hasattr(out, '__iter__'):
            raise TypeError('Request handler for route "%s" returned [%s] '
            'which is not iterable.' % (request_thread_local.path, type(out).__name__))
        return out


    def __call__(self, environ, start_response):
        """ The Sparrow WSGI-interface. """
        request_thread_local.bind(environ)
        response_thread_local.bind()
        try: # Unhandled Exceptions
            try: # Sparrow Error Handling
                if not self.serve:
                    abort(503, "Server stopped")
                handler, args = self.match_url(request_thread_local.path, request_thread_local.method)
                if not handler:
                    raise HTTPError(404, "Not found")
                output = handler(**args)
            except BreakTheSparrow, e:
                output = e.output_fp
            except HTTPError, e:
                response_thread_local.status = e.http_status
                output = self.error_handler.get(response_thread_local.status, str)(e)
            output = self.cast(output)
            if response_thread_local.status in (100, 101, 204, 304) or request_thread_local.method == 'HEAD':
                output = [] # rfc2616 section 4.3
        except (KeyboardInterrupt, SystemExit, MemoryError):
            raise
        except Exception as e:
            response_thread_local.status = 500
            if self.catchall:
                err = "Unhandled Exception: %s\n" % (repr(e))
                err += TRACEBACK_TEMPLATE % traceback.format_exc(10)
                output = [str(HTTPError(500, err))]
                request_thread_local._environ['wsgi.errors'].write(err)
            else:
                raise
        status = '%d %s' % (response_thread_local.status, HTTP_CODES[response_thread_local.status])
        start_response(status, response_thread_local.wsgiheaders())
        return output

