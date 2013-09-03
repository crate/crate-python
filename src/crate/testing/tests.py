import unittest
import doctest
import os
import requests
import random

from .layer import CrateLayer


def docs_path(*parts):
    return os.path.join(os.path.dirname(os.path.dirname(__file__)), *parts)

def crate_path(*parts):
    return docs_path('..', '..', 'parts', 'crate', *parts)


def test_crate_layer():
    """ Test the layer by starting it, issuing an request and stopping it.

    >>> crate_layer =  CrateLayer('crate-test-'+str(random.randint(1, 10000)),
    ...                          crate_home=crate_path(),
    ...                          crate_exec=crate_path('bin', 'crate'),
    ...                          port=19200,)
    >>> crate_layer.start()
    >>> res = requests.get('http://127.0.0.1:19200/_stats')
    >>> res.status_code
    200
    >>> crate_layer.stop()

    """

def test_suite():
    suite = unittest.TestSuite()
    suite.addTest(doctest.DocTestSuite())
    return suite

