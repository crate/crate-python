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

# Default variables.
BUILDOUT_VERSION=${BUILDOUT_VERSION:-2.13.7}
CRATEDB_VERSION=${CRATEDB_VERSION:-5.0.1}
SQLALCHEMY_VERSION=${SQLALCHEMY_VERSION:-1.4.44}


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

    # Install Buildout with designated version, allowing pre-releases.
    pip install --pre "zc.buildout==${BUILDOUT_VERSION}"

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
    echo "Sandbox environment ready"
    echo -n "Using SQLAlchemy version: "
    python -c 'import sqlalchemy; print(sqlalchemy.__version__)'
    echo

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
    flake8 "$@" src bin
}

main
