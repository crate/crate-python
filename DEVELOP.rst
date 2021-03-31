===============
Developer guide
===============

Setup
=====

This project uses buildout_ to set up the development environment.

To start things off, create a Python virtualenv and install buildout::

    python3 -m venv .venv
    source .venv/bin/activate

    # Workaround for Python 3.5
    python -m pip install --upgrade "setuptools>=31,<51"

    pip install zc.buildout==2.13.4

Then, run::

    buildout -N

Running tests
=============

All tests will be invoked using the Python interpreter that was used when
creating the Python virtualenv. The test runner is zope.testrunner_.

Run all tests::

    ./bin/test

Run specific tests::

    # Ignore all tests below src/crate/testing
    ./bin/test -vvvv --ignore_dir=testing

You can run the tests against multiple Python interpreters with tox_::

    ./bin/tox

To do this, you will need the respective Python interpreter versions available
on your ``$PATH``.

To run against a single interpreter, you can also invoke::

    ./bin/tox -e py37

*Note*: before running the tests, make sure to stop all CrateDB instances which
are listening on the default CrateDB transport port to avoid side effects with
the test layer.

Preparing a release
===================

To create a new release, you must:

- Backport your bug fixes to the latest stable branch x.y (e.g. 0.19)

- For new features, create a new stable branch x.(y+1) (e.g. 0.20)

In the release branch:

- Update ``__version__`` in ``src/crate/client/__init__.py``

- Add a section for the new version in the ``CHANGES.txt`` file

- Commit your changes with a message like "prepare release x.y.z"

- Push to origin/<release_branch>

- Create a tag by running ``./devtools/create_tag.sh``. This will trigger a
  Github action which releases the new version to PyPi.

On master:

- Update the release notes to reflect the release

Next:

- Archive docs for old releases (see section below)

Archiving docs versions
-----------------------

Check the `versions hosted on ReadTheDocs`_.

We should only be hosting the docs for `latest`, `stable`, and the most recent
patch versions for the last two minor releases.

To make changes to the RTD configuration (e.g., to activate or deactivate a
release version), please contact the `@crate/docs`_ team.

Writing documentation
=====================

The docs live under the ``docs`` directory.

The docs are written written with ReStructuredText_ and processed with Sphinx_.

Build the docs by running::

    ./bin/sphinx

The output can then be found in the ``out/html`` directory.

The docs are automatically built from Git by `Read the Docs`_ and there is
nothing special you need to do to get the live docs to update.

.. _@crate/docs: https://github.com/orgs/crate/teams/docs
.. _buildout: https://pypi.python.org/pypi/zc.buildout
.. _PyPI: https://pypi.python.org/pypi
.. _Read the Docs: http://readthedocs.org
.. _ReStructuredText: http://docutils.sourceforge.net/rst.html
.. _Sphinx: http://sphinx-doc.org/
.. _tox: http://testrun.org/tox/latest/
.. _twine: https://pypi.python.org/pypi/twine
.. _zope.testrunner: https://pypi.python.org/pypi/zope.testrunner/4.4.1
.. _versions hosted on ReadTheDocs: https://readthedocs.org/projects/crate-python/versions/
