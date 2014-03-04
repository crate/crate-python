#!/bin/bash
WORKING_DIR=`dirname $0`
VENV_DIR="${WORKING_DIR}/venv"
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
PYTHON_EXECUTABLE=./${VENV_DIR}/bin/python
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
