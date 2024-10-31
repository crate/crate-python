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
CRATEDB_VERSION=${CRATEDB_VERSION:-5.9.2}


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
    pip install --pre --requirement=requirements.txt

}

function setup_package() {

    # Upgrade `pip` to support `--pre` option.
    pip install --upgrade pip

    # Conditionally add `--pre` option, to allow installing prerelease packages.
    PIP_OPTIONS="${PIP_OPTIONS:-}"
    if [ "${PIP_ALLOW_PRERELEASE}" == "true" ]; then
      PIP_OPTIONS+=" --pre"
    fi

    # Install package in editable mode.
    pip install ${PIP_OPTIONS} --editable='.[test]'

}

function run_buildout() {
    buildout -N
}

function finalize() {

    # Some steps before dropping into the activated virtualenv.
    echo
    echo "Sandbox environment ready"
    echo

}

function activate_uv() {
  if command -v uv; then
    function pip() {
      uv pip "$@"
    }
  fi
}
function deactivate_uv() {
  unset -f pip
}

function main() {
    activate_uv
    ensure_virtualenv
    activate_virtualenv
    before_setup
    setup_package
    run_buildout
    deactivate_uv
    finalize
}

function lint() {
    poe lint
}

main
