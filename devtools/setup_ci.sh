#!/bin/bash

set -e

function args() {
  options=$(getopt --long cratedb-version: --long sqlalchemy-version: -- "$@")
  [ $? -eq 0 ] || {
    echo "Incorrect options provided"
    exit 1
  }
  eval set -- "$options"
  while true; do
      case "$1" in
      --cratedb-version)
          shift;
          cratedb_version=$1
          ;;
      --sqlalchemy-version)
          shift;
          sqlalchemy_version=$1
          ;;
      --)
          shift
          break
          ;;
      esac
      shift
  done
}

function main() {

  # Read command line arguments.
  args $0 "$@"

  # Sanity checks.
  [ -z ${cratedb_version} ] && {
    echo "--cratedb-version must be given"
    exit 1
  }
  [ -z ${sqlalchemy_version} ] && {
    echo "--sqlalchemy-version must be given"
    exit 1
  }

  # Let's go.
  echo "Invoking tests with CrateDB ${cratedb_version} and SQLAlchemy ${sqlalchemy_version}"

  python -m pip install --upgrade pip

  # Workaround needed for Python 3.5
  python -m pip install --upgrade "setuptools>=31,<51"

  pip install zc.buildout==2.13.4

  # Replace SQLAlchemy version.
  sed -ir "s/SQLAlchemy.*/SQLAlchemy = ${sqlalchemy_version}/g" versions.cfg

  # Replace CrateDB version.
  if [ ${cratedb_version} = "nightly" ]; then
    sed -ir "s/releases/releases\/nightly/g" base.cfg
    sed -ir "s/crate_server.*/crate_server = latest/g" versions.cfg
  else
    sed -ir "s/crate_server.*/crate_server = ${cratedb_version}/g" versions.cfg
  fi

  buildout -n -c base.cfg

}

main "$@"
