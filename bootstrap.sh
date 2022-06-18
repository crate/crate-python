#!/bin/bash
#
# Bootstrap sandbox environment for crate-python
#
# - Create a Python virtualenv
# - Install all dependency packages and modules
# - Install package in editable mode
# - Drop user into an activated virtualenv
#
# Synopsis::
#
#     source bootstrap.sh
#


# Trace all invocations.
# set -x


function print_header() {
    printf '=%.0s' {1..42}; echo
    echo "$1"
    printf '=%.0s' {1..42}; echo
}

function ensure_virtualenv() {
    # Create a Python virtualenv with current version of Python 3.
    # TODO: Maybe take `pyenv` into account.
    if [[ ! -d .venv ]]; then
        python3 -m venv .venv
    fi
}

function activate_virtualenv() {
    # Activate Python virtualenv.
    source .venv/bin/activate
}

function before_setup() {

    # When `wheel` is installed, Python will build `wheel` packages from all
    # acquired `sdist` packages and will store them into `~/.cache/pip`, where
    # they will be picked up by the caching machinery and will be reused on
    # subsequent invocations when run on CI. This makes a *significant*
    # difference on total runtime on CI, it is about 2x faster.
    #
    # Otherwise, there will be admonitions like:
    #   Using legacy 'setup.py install' for foobar, since package 'wheel' is
    #   not installed.
    #
    pip install wheel

    BUILDOUT_VERSION=${BUILDOUT_VERSION:-2.13.7}
    pip install "zc.buildout==${BUILDOUT_VERSION}"

}

function setup_package() {

    # Install package in editable mode.
    pip install --editable=.[sqlalchemy,test,doc]

}

function run_buildout() {
    buildout -N
}

function finalize() {

    # Some steps before dropping into the activated virtualenv.
    echo
    python -c 'import sqlalchemy; print(f"SQLAlchemy version: {sqlalchemy.__version__}")'

}

function main() {
    ensure_virtualenv
    activate_virtualenv
    before_setup
    setup_package
    run_buildout
    finalize
}

function lint() {
    flake8
}

main
