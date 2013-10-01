
from __future__ import absolute_import
import sys

py2 = True
if sys.version_info[0] > 2:
    py2 = False


if py2:
    from exceptions import StandardError
    xrange = xrange

    def cprint(s):
        print(s)
else:
    StandardError = Exception
    xrange = range

    def cprint(s):
        if isinstance(s, bytes):
            s = s.decode('utf-8')
        print(s)


assert StandardError
