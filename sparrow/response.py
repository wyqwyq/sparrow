import threading
from wsgiref.headers import Headers as HeaderWrapper
from Cookie import SimpleCookie

class Response(threading.local):
    """ Represents a single response using thread-local namespace. """

    def bind(self):
        """ Clears old data and creates a brand new Response object """
        self._COOKIES = None
        self.status = 200
        self.header_list = []
        self.header = HeaderWrapper(self.header_list)
        self.content_type = 'text/html'
        self.error = None
        self.charset = 'utf8'

    def wsgiheaders(self):
        ''' Returns a wsgi conform list of header/value pairs '''
        for c in self.COOKIES.itervalues():
            self.header.add_header('Set-Cookie', c.OutputString())
        return [(h.title(), str(v)) for h, v in self.header.items()]

    @property
    def COOKIES(self):
        if not self._COOKIES:
            self._COOKIES = SimpleCookie()
        return self._COOKIES

    def set_cookie(self, key, value, **kargs):
        """
        Sets a Cookie. Optional settings:
        expires, path, comment, domain, max-age, secure, version, httponly
        """
        self.COOKIES[key] = value
        for k, v in kargs.iteritems():
            self.COOKIES[key][k] = v

    def get_content_type(self):
        """ Get the current 'Content-Type' header. """
        return self.header['Content-Type']
        
    def set_content_type(self, value):
        if 'charset=' in value:
            self.charset = value.split('charset=')[-1].split(';')[0].strip()
        self.header['Content-Type'] = value

    content_type = property(get_content_type, set_content_type, None,
                            get_content_type.__doc__)
response = Response()