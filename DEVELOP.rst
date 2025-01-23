==============================
CrateDB Python developer guide
==============================

Setup
=====

Optionally install Python package and project manager `uv`_,
in order to significantly speed up the package installation::

    {apt,brew,pip,zypper} install uv
    alias pip="uv pip"

To start things off, bootstrap the sandbox environment::

    git clone https://github.com/crate/crate-python
    cd crate-python
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

    poe test

Run specific tests::

    # Select modules.
    bin/test -t test_cursor
    bin/test -t client
    bin/test -t testing

    # Select doctests.
    bin/test -t http.rst

Ignore specific test directories::

    bin/test --ignore_dir=testing

The ``LayerTest`` test cases have quite some overhead. Omitting them will save
a few cycles (~70 seconds runtime)::

    bin/test -t '!LayerTest'

Invoke all tests without integration tests (~10 seconds runtime)::

    bin/test --layer '!crate.testing.layer.crate' --test '!LayerTest'

Yet ~60 test cases, but only ~1 second runtime::

    bin/test --layer '!crate.testing.layer.crate' --test '!LayerTest' \
        -t '!test_client_threaded' -t '!test_no_retry_on_read_timeout' \
        -t '!test_wait_for_http' -t '!test_table_clustered_by'

To inspect the whole list of test cases, run::

    bin/test --list-tests

The CI setup on GitHub Actions (GHA) provides a full test matrix covering
relevant Python versions. You can invoke the software tests against a specific
Python interpreter or multiple `Python versions`_ on your workstation using
`uv`_, by supplying the ``--python`` command-line option, or by defining the
`UV_PYTHON`_ environment variable prior to invoking ``source bootstrap.sh``.

*Note*: Before running the tests, make sure to stop all CrateDB instances which
are listening on the default CrateDB transport port to avoid side effects with
the test layer.


Formatting and linting code
===========================

To use Ruff for code formatting, according to the standards configured in
``pyproject.toml``, use::

    poe format

To lint the code base using Ruff and mypy, use::

    poe lint

Linting and software testing, all together now::

    poe check


Renew certificates
==================

For conducting TLS connectivity tests, there are a few X.509 certificates at
`tests/assets/pki/*.pem`_. In order to renew them, follow the instructions
within the README file in this folder.


Preparing a release
===================

To create a new release, you must:

- Backport your bug fixes to the latest stable branch x.y (e.g. 0.19)

- For new features, create a new stable branch x.(y+1) (e.g. 0.20)

In the release branch:

- Update ``__version__`` in ``src/crate/client/__init__.py``

- Add a section for the new version in the ``CHANGES.rst`` file

- Commit your changes with a message like "prepare release x.y.z"

- Push to origin/<release_branch>

- Create a tag by running ``./devtools/create_tag.sh``. This will trigger a
  Github action which releases the new version to PyPi.

On branch ``main``:

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
.. _Python versions: https://docs.astral.sh/uv/concepts/python-versions/
.. _Read the Docs: http://readthedocs.org
.. _ReStructuredText: http://docutils.sourceforge.net/rst.html
.. _Sphinx: http://sphinx-doc.org/
.. _tests/assets/pki/*.pem: https://github.com/crate/crate-python/tree/main/tests/assets/pki
.. _twine: https://pypi.python.org/pypi/twine
.. _useful command-line options for zope-testrunner: https://pypi.org/project/zope.testrunner/#some-useful-command-line-options-to-get-you-started
.. _uv: https://docs.astral.sh/uv/
.. _UV_PYTHON: https://docs.astral.sh/uv/configuration/environment/#uv_python
.. _versions hosted on ReadTheDocs: https://readthedocs.org/projects/crate-python/versions/
.. _zope.testrunner: https://pypi.org/project/zope.testrunner/
