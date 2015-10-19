import os
import socket
import unittest
import doctest

def docs_path(*parts):
    return os.path.join(os.path.dirname(os.path.dirname(__file__)), *parts)

def crate_path(*parts):
    return os.path.abspath(docs_path('..', '..', 'parts', 'crate', *parts))

def public_ip():
    """
    take first public interface
    sorted by getaddrinfo - see RFC 3484
    should have the real public IPv4 address as first address.
    At the moment the test layer is not able to handle v6 addresses
    """
    for addrinfo in socket.getaddrinfo(socket.gethostname(), None):
        if addrinfo[1] in (socket.SOCK_STREAM, socket.SOCK_DGRAM) and addrinfo[0] == socket.AF_INET:
            return addrinfo[4][0]
    # fallback
    return socket.gethostbyname(socket.gethostname())

def setUp(test):
    test.globs['crate_path'] = crate_path
    test.globs['public_ip'] = public_ip()

def test_suite():
    suite = unittest.TestSuite()

    s = doctest.DocFileSuite('layer.txt',
                             setUp=setUp,
                             optionflags=doctest.NORMALIZE_WHITESPACE |
                                         doctest.ELLIPSIS)
    suite.addTest(s)
    return suite
