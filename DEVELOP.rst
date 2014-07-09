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


Deployment to Pypi
==================

To create the packages use::

    bin/py setup.py sdist bdist_wheel

and then use `twine <https://pypi.python.org/pypi/twine>`_ to upload the
packages::

    twine upload dist/*

If twine is not installed locally the regular setup.py upload can also be used,
but does only support plaintext authentication::

    bin/py setup.py upload

In order to verify that the description that is uploaded to PYPI will be
rendered correctly the following command can be used::

    bin/py setup.py check --strict --restructuredtext

Writing Documentation
=====================

The documentation is maintained under the ``docs`` directory and
written in ReStructuredText_ and processed with Sphinx_.

Normally the documentation is built by `Read the Docs`_.
However if you work on the documentation you can run sphinx
directly, which can be done by just running ``bin/sphinx``.
The output can then be found in the ``out/html``  directory.

.. _Sphinx: http://sphinx-doc.org/

.. _ReStructuredText: http://docutils.sourceforge.net/rst.html

.. _`Read the Docs`: http://readthedocs.org
