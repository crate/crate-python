
from __future__ import absolute_import
import sys

py2 = True
if sys.version_info[0] > 2:
    py2 = False


if py2:
    from exceptions import StandardError
    xrange = xrange
    raw_input = raw_input
    unicode = unicode

    def cprint(s):
        print(s)

    import Queue
    queue = Queue

    import BaseHTTPServer

    def to_bytes(data, *args, **kwargs):
        return data

else:
    StandardError = Exception
    xrange = range
    raw_input = input
    unicode = str

    def cprint(s):
        if isinstance(s, bytes):
            s = s.decode('utf-8')
        print(s)

    import queue
    assert queue

    import http.server
    BaseHTTPServer = http.server
    to_bytes = bytes

assert StandardError
