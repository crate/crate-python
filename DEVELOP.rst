==============================
CrateDB Python developer guide
==============================

Setup
=====

Clone the repository::

    git clone https://github.com/crate/crate-python
    cd crate-python

Setup a virtualenv and install the package::

    python -m venv .venv
    source .venv/bin/activate
    python -m pip install --group dev --group docs -e .

Or if using `uv`_::

    uv venv .venv
    source .venv/bin/activate
    uv pip install --group dev --group docs -e .


Running tests
=============

Ensure the virtualenv is active and run tests using `pytest`_::

    python -m pytest


See also:

- `How to invoke pytest <https://docs.pytest.org/en/stable/how-to/usage.html>` for more information.


Formatting and linting code
===========================

Use `ruff`_ for code formatting and linting::

    ruff format --check .
    ruff check .


Use ``mypy`` for type checking::

    mypy

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

- Add a section for the new version in the ``CHANGES.rst`` file

- Commit your changes with a message like "prepare release x.y.z"

- Push to origin/<release_branch>

- Create a tag by running ``git tag -s <version>`` and push it ``git push --tags``.
  This will trigger a Github action which releases the new version to PyPi.

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

The docs are written with ReStructuredText_ and processed with Sphinx_.

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
.. _pytest: https://docs.pytest.org/en/stable/
