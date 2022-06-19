#!/bin/bash

set -e

function main() {

  # Sanity checks.
  [ -z ${CRATEDB_VERSION} ] && {
    echo "--cratedb-version must be given"
    echo "Environment variable 'CRATEDB_VERSION' needed"
    exit 1
  }
  [ -z ${SQLALCHEMY_VERSION} ] && {
    echo "Environment variable 'SQLALCHEMY_VERSION' needed"
    exit 1
  }

  # Let's go.
  echo "Invoking tests with CrateDB ${CRATEDB_VERSION} and SQLAlchemy ${SQLALCHEMY_VERSION}"

  # Install designated SQLAlchemy version.
  pip install "sqlalchemy==${SQLALCHEMY_VERSION}"

  # Replace CrateDB version.
  if [ ${CRATEDB_VERSION} = "nightly" ]; then
    sed -ir "s/releases/releases\/nightly/g" buildout.cfg
    sed -ir "s/crate_server.*/crate_server = latest/g" versions.cfg
  else
    sed -ir "s/crate_server.*/crate_server = ${CRATEDB_VERSION}/g" versions.cfg
  fi

}

main "$@"
