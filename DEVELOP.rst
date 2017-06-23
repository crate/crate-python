===============
Developer Guide
===============

Setup
=====

This project uses buildout_ to set up the development environment.

To start things off, run::

    $ python bootstrap.py

Then, run::

    $ ./bin/buildout -N

Running Tests
=============

The tests are run using the zope.testrunner_::

    $ ./bin/test

This will run all tests using the Python interpreter that was used to
bootstrap buildout.

You can run the tests against multiple Python interpreters with tox_::

    $ ./bin/tox

To do this, you will need ``python2.7``, ``python3.3``, and ``pypy`` on your
``$PATH``.

To run against a single interpreter, you can also do::

    $ ./bin/tox -e py33

*Note*: before running tests make sure to stop all CrateDB instances which
listening on the default CrateDB transport port to avoid side effects with the
test layer.

Preparing a Release
===================

To create a new release, you must:

- Backport your bug fixes to the latest stable branch x.y (e.g. 0.19)

- For new features, create a new stable branch x.(y+1) (e.g. 0.20)

In the release branch:

- Update ``__version__`` in ``src/crate/client/__init__.py``

- Add a section for the new version in the ``CHANGES.txt`` file

- Commit your changes with a message like "prepare release x.y.z"

- Push to origin/<release_branch>

- Create a tag by running ``./devtools/create_tag.sh``

On master:

- Update the release notes to reflect the release

Next:

- Deploy to PyPI (see section below)

- Archive docs for old releases (see section below)

PyPI Deployment
---------------

To create the package use::

    $ bin/py setup.py sdist bdist_wheel

Then, use twine_ to upload the package to PyPI_::

    $ bin/twine upload dist/*

For this to work, you will need a personal PyPI account that is set up as a project admin.

You'll also need to create a ``~/.pypirc`` file, like so::

    [distutils]
    index-servers =
      pypi

    [pypi]
    repository=https://pypi.python.org/pypi
    username=<USERNAME>
    password=<PASSWORD>

Here, ``<USERNAME>`` and ``<PASSWORD>`` should be replaced with your username and password, respectively.

If you want to check the PyPI description before uploading, run::

    $ bin/py setup.py check --strict --restructuredtext

Archiving Docs Versions
-----------------------

Check the `versions hosted on ReadTheDocs`_.

We should only be hosting the docs for `latest`, `stable`, and the most recent
patch versions for the last two minor releases.

Sometimes you might find that there are multiple older releases that need to be
archived.

You can archive releases by selecting *Edit*, unselecting the *Active*
checkbox, and then saving.

Writing Documentation
=====================

The docs live under the ``docs`` directory.

The docs are written written with ReStructuredText_ and processed with Sphinx_.

Build the docs by running::

    $ bin/sphinx

The output can then be found in the ``out/html`` directory.

The docs are automatically built from Git by `Read the Docs`_ and there is
nothing special you need to do to get the live docs to update.

.. _buildout: https://pypi.python.org/pypi/zc.buildout
.. _PyPI: https://pypi.python.org/pypi
.. _Read the Docs: http://readthedocs.org
.. _ReStructuredText: http://docutils.sourceforge.net/rst.html
.. _Sphinx: http://sphinx-doc.org/
.. _tox: http://testrun.org/tox/latest/
.. _twine: https://pypi.python.org/pypi/twine
.. _zope.testrunner: https://pypi.python.org/pypi/zope.testrunner/4.4.1
.. _versions hosted on ReadTheDocs: https://readthedocs.org/projects/crate-python/versions/
