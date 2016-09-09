
import re
import traceback

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

    def add_route(self, route, handler, method='GET', simple=False, **kargs):
        """ Adds a new route to the route mappings. """
        if isinstance(handler, type) and issubclass(handler, BaseController):
            handler = handler()
        if isinstance(handler, BaseController):
            self.add_controller(route, handler, method=method, simple=simple, **kargs)
            return
        method = method.strip().upper()
        route = route.strip().lstrip('$^/ ').rstrip('$^ ')
        if re.match(r'^(\w+/)*\w*$', route) or simple:
            self.simple_routes.setdefault(method, {})[route] = handler
        else:
            route = re.sub(r':([a-zA-Z_]+)(?P<uniq>[^\w/])(?P<re>.+?)(?P=uniq)',
                           r'(?P<\1>\g<re>)',route)
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
            response.content_type = 'application/json'
        elif not out:
            out = []
            response.header['Content-Length'] = '0'
        elif isinstance(out, types.StringType):
            out = [out]
        elif isinstance(out, unicode):
            out = [out.encode(response.charset)]
        elif isinstance(out, list) and isinstance(out[0], unicode):
            out = map(lambda x: x.encode(response.charset), out)
        elif hasattr(out, 'read'):
            def readcloser(f):
                while True:
                    data = f.read(8192)
                    if not data:
                        f.close()
                        break
                    else:
                        yield data
            out = request.environ.get('wsgi.file_wrapper', readcloser)(out)
        if isinstance(out, list) and len(out) == 1:
            response.header['Content-Length'] = str(len(out[0]))
        if not hasattr(out, '__iter__'):
            raise TypeError('Request handler for route "%s" returned [%s] '
            'which is not iterable.' % (request.path, type(out).__name__))
        return out


    def __call__(self, environ, start_response):
        """ The bottle WSGI-interface. """
        request.bind(environ)
        response.bind()
        try: # Unhandled Exceptions
            try: # Sparrow Error Handling
                if not self.serve:
                    abort(503, "Server stopped")
                handler, args = self.match_url(request.path, request.method)
                if not handler:
                    raise HTTPError(404, "Not found")
                output = handler(**args)
                db.close()
            except BreakTheSparrow, e:
                output = e.output_fp
            except HTTPError, e:
                response.status = e.http_status
                output = self.error_handler.get(response.status, str)(e)
            output = self.cast(output)
            if response.status in (100, 101, 204, 304) or request.method == 'HEAD':
                output = [] # rfc2616 section 4.3
        except (KeyboardInterrupt, SystemExit, MemoryError):
            raise
        except Exception as e:
            response.status = 500
            if self.catchall:
                err = "Unhandled Exception: %s\n" % (repr(e))
                err += TRACEBACK_TEMPLATE % traceback.format_exc(10)
                output = [str(HTTPError(500, err))]
                request._environ['wsgi.errors'].write(err)
            else:
                raise
        status = '%d %s' % (response.status, HTTP_CODES[response.status])
        start_response(status, response.wsgiheaders())
        return output
