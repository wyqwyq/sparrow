# -*- coding: utf-8 -*-
import threading
from Cookie import SimpleCookie
import cgi

class Request(threading.local):
    def bind(self, environ):
        """
        绑定一个环境变量，设置GET、POST、COOKIE及path
        """
        self._environ = environ
        self.environ = environ
        self._GET = None
        self._POST = None
        self._COOKIES = None
        self.path = self._environ.get('PATH_INFO', '/').strip()
        if not self.path.startswith('/'):
            self.path = '/' + self.path

    @property
    def method(self):
        """
        获取请求方法，默认GET
        """
        return self._environ.get('REQUEST_METHOD', 'GET').upper()

    @property
    def query_string(self):
        """
        获取query string，默认为空
        """
        return self._environ.get('QUERY_STRING', '')

    @property
    def input_length(self):
        "获取输入长度，默认为0"
        try:
            return int(self._environ.get('CONTENT_LENGTH', '0'))
        except ValueError:
            return 0

    @property
    def GET(self):
        """ Get a dict with GET parameters. """
        if self._GET is None:
            data = cgi.parse_qs(self.query_string, keep_blank_values=True)
            self._GET = {}
            for key, value in data.items():
                if len(value) == 1:
                    self._GET[key] = value[0]
                else:
                    self._GET[key] = value
        return self._GET

    @property
    def POST(self):
        if self._POST is None:
            data = cgi.FieldStorage(fp=self._environ['wsgi.input'],
                environ=self._environ, keep_blank_values=True)
            self._POST  = {}
            for item in data.list or []:
                name = item.name
                if not item.filename:
                    item = item.value
                self._POST.setdefault(name, []).append(item)
            for key in self._POST:
                if len(self._POST[key]) == 1:
                    self._POST[key] = self._POST[key][0]
        return self._POST

    @property
    def COOKIES(self):
        if self._COOKIES is None:
            raw_dict = SimpleCookie(self._environ.get('HTTP_COOKIE',''))
            self._COOKIES = {}
            for cookie in raw_dict.itervalues():
                self._COOKIES[cookie.key] = cookie.value
        return self._COOKIES

request = Request()