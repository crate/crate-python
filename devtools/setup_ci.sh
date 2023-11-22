#!/bin/bash

set -e

function main() {

  # Sanity checks.
  [ -z ${CRATEDB_VERSION} ] && {
    echo "Environment variable 'CRATEDB_VERSION' needed"
    exit 1
  }

  # Replace CrateDB version.
  if [ ${CRATEDB_VERSION} = "nightly" ]; then
    sed -ir "s!releases/cratedb/x64_linux!releases/nightly!g" buildout.cfg
    sed -ir "s/crate_server.*/crate_server = latest/g" versions.cfg
  else
    sed -ir "s/crate_server.*/crate_server = ${CRATEDB_VERSION}/g" versions.cfg
  fi

}

main "$@"
