===============
Developer guide
===============

Setup
=====

To start things off, bootstrap the sandbox environment::

    source bootstrap.sh

This command should automatically install all prerequisites for the development
sandbox and drop you into the virtualenv, ready for invoking further commands.


Running tests
=============

All tests will be invoked using the Python interpreter that was used when
creating the Python virtualenv. The test runner is `zope.testrunner`_.

Some examples are outlined below. In order to learn about more details,
see, for example, `useful command-line options for zope-testrunner`_.

Run all tests::

    ./bin/test -vvvv

Run specific tests::

    ./bin/test -vvvv -t SqlAlchemyCompilerTest
    ./bin/test -vvvv -t test_score
    ./bin/test -vvvv -t sqlalchemy

Ignore specific test directories::

    ./bin/test -vvvv --ignore_dir=testing

The ``LayerTest`` test cases have quite some overhead. Omitting them will save
a few cycles (~70 seconds runtime)::

    ./bin/test -t '!LayerTest'

Invoke all tests without integration tests (~15 seconds runtime)::

    ./bin/test --layer '!crate.testing.layer.crate' --test '!LayerTest'

Yet ~130 test cases, but only ~5 seconds runtime::

    ./bin/test --layer '!crate.testing.layer.crate' --test '!LayerTest' \
        -t '!test_client_threaded' -t '!test_no_retry_on_read_timeout' \
        -t '!test_wait_for_http' -t '!test_table_clustered_by'

To inspect the whole list of test cases, run::

    ./bin/test --list-tests

You can run the tests against multiple Python interpreters with `tox`_::

    tox

To do this, you will need the respective Python interpreter versions available
on your ``$PATH``.

To run against a single interpreter, you can also invoke::

    tox -e py37

*Note*: Before running the tests, make sure to stop all CrateDB instances which
are listening on the default CrateDB transport port to avoid side effects with
the test layer.


Renew certificates
==================

For conducting TLS connectivity tests, there are a few X.509 certificates at
`src/crate/client/pki/*.pem`_. In order to renew them, follow the instructions
within the README file in this folder.


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
.. _src/crate/client/pki/*.pem: https://github.com/crate/crate-python/tree/master/src/crate/client/pki
.. _tox: http://testrun.org/tox/latest/
.. _twine: https://pypi.python.org/pypi/twine
.. _useful command-line options for zope-testrunner: https://pypi.org/project/zope.testrunner/#some-useful-command-line-options-to-get-you-started
.. _versions hosted on ReadTheDocs: https://readthedocs.org/projects/crate-python/versions/
.. _zope.testrunner: https://pypi.org/project/zope.testrunner/
