
from __future__ import absolute_import
import sys

py2k = True
if sys.version_info[0] > 2:
    py2k = False


if py2k:
    from exceptions import StandardError

    def cprint(s):
        print(s)
else:
    StandardError = Exception

    def cprint(s):
        if isinstance(s, bytes):
            s = s.decode('utf-8')
        print(s)


assert StandardError
