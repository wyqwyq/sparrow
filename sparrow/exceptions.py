# -*- coding: utf-8 -*-

from request import request
from common import HTTP_ERROR_TEMPLATE, HTTP_CODES

class SparrowException(Exception):
    """ A base class for exceptions used by sparrow. """
    pass


class HTTPError(SparrowException):
    """
    This class is used to break the execution and then jump to an error
    handler. 
    """
    def __init__(self, status, text):
        self.output = text
        self.http_status = int(status)
        super(HTTPError, self).__init__(status, text)

    def __repr__(self):
        return 'HTTPError(%d,%s)' % (self.http_status, repr(self.output))

    def __str__(self):
        return HTTP_ERROR_TEMPLATE % {
            'status' : self.http_status,
            'url' : request.path,
            'error_name' : HTTP_CODES.get(self.http_status, 'Unknown').title(),
            'error_message' : ''.join(self.output)
        }


class BreakTheSparrow(SparrowException):
    '''
    Used to instantly break the execution of request handler.
    '''
    def __init__(self, output_fp):
        self.output_fp = output_fp

