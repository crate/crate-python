#!/bin/bash

if [[ -d './dependencies' ]]; then
    rm -rf ./dependencies/*
fi


if [[ -d './eggs' ]]; then
    rm -rf ./eggs
fi

python bootstrap.py
bin/buildout -N

if [[ ! -d './dependencies' ]]; then
    mkdir "dependencies"
fi

rm -rf eggs/zc.*.egg

find ./eggs -type f -name "*.pyc" -delete
find ./eggs -type d -name "__pycache__" -delete
find ./eggs -depth -type d -name "EGG-INFO" -exec rm -rf {} \;

cp -a eggs/*/* dependencies/

echo "from crate.client.crash import main; main()" > dependencies/__main__.py

cd dependencies
zip -r crate.zip ./*
cd ../
mv dependencies/crate.zip crash.zip.py
