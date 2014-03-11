#!/bin/bash

# Licensed to CRATE Technology GmbH ("Crate") under one or more contributor
# license agreements.  See the NOTICE file distributed with this work for
# additional information regarding copyright ownership.  Crate licenses
# this file to you under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.  You may
# obtain a copy of the License at
#
#   http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS, WITHOUT
# WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.  See the
# License for the specific language governing permissions and limitations
# under the License.
#
# However, if you have executed another commercial license agreement
# with Crate these terms will supersede the license and you may use the
# software solely pursuant to the terms of the relevant commercial agreement.

WORKING_DIR=`dirname $0`
VENV_DIR="venv"
VERSION=`sed -n 's/^__version__ = "\(.*\)".*$/\1/p' ${WORKING_DIR}/../src/crate/client/__init__.py`
BUNDLE_FILE="crash-${VERSION}.zip.py"


pushd ${WORKING_DIR}
if [[ -e ${BUNDLE_FILE} ]]; then
    rm ${BUNDLE_FILE}
fi

if [[ -d './dependencies' ]]; then
    rm -rf ./dependencies/*
fi


if [[ -d './eggs' ]]; then
    rm -rf ./eggs
fi

if [[ -z `which virtualenv` ]]; then
    echo "virtualenv not found. please install virtualenv"
    exit 1
fi

mkdir -p venv
virtualenv --no-site-packages --clear ${VENV_DIR}
PYTHON_EXECUTABLE=${VENV_DIR}/bin/python
${VENV_DIR}/bin/easy_install readline
${PYTHON_EXECUTABLE} bootstrap.py
${PYTHON_EXECUTABLE} bin/buildout -N

if [[ ! -d './dependencies' ]]; then
    mkdir -p './dependencies'
fi

rm -rf ./eggs/zc.*.egg

find ./eggs -type f -name "*.pyc" -delete
find ./eggs -type d -name "__pycache__" -delete
find ./eggs -depth -type d -name "EGG-INFO" -exec rm -rf {} \;

cp -a ./eggs/*/* ./dependencies/

echo "from crate.client.crash import main; main()" > dependencies/__main__.py

pushd dependencies
zip -r crate.zip ./*
popd
mv dependencies/crate.zip ${BUNDLE_FILE}

echo "#!/usr/bin/env python" | cat - ${BUNDLE_FILE} > tmpfile
mv tmpfile ${BUNDLE_FILE}
chmod u+x ${BUNDLE_FILE}
echo "created ${BUNDLE_FILE}"

popd
