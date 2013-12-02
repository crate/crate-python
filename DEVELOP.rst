========================
Crate-Python Development
========================


Development Setup
=================

To get a development environment crate-python uses `buildout
<https://pypi.python.org/pypi/zc.buildout/2.2.1>`_

Run `bootstrap.py`::

    python bootstrap.py

And afterwards run buildout::

    ./bin/buildout -N

Running Tests
=============

The tests are run using the `zope.testrunner
<https://pypi.python.org/pypi/zope.testrunner/4.4.1>`_::

    ./bin/test

This will run all tests using the python interpreter that was used to
bootstrap buildout.

In addition to that it is also possible to run the test case against multiple
python interpreter using `tox <http://testrun.org/tox/latest/>`_::

    ./bin/tox

This required the interpreters `python2.7`, `python3.3` and `pypy` to be
available in `$PATH`. To run against a single interpreter tox can also be
invoked like this::

    ./bin/tox -e py33

Note: Before running tests make sure to stop all crate instances which
transport port is listening on port 9300 to avoid side effects with the test
layer.
