#!/bin/bash
#
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

# check if everything is committed
CLEAN=`git status -s`
if [ ! -z "$CLEAN" ]
then
   echo "Working directory not clean. Please commit all changes before tagging"
   echo "Aborting."
   exit -1
fi

echo "Fetching origin..."
git fetch origin > /dev/null

# get current branch
BRANCH=`git branch | grep "^*" | cut -d " " -f 2`
echo "Current branch is $BRANCH."

# check if main == origin/main
LOCAL_COMMIT=`git show --format="%H" $BRANCH`
ORIGIN_COMMIT=`git show --format="%H" origin/$BRANCH`

if [ "$LOCAL_COMMIT" != "$ORIGIN_COMMIT" ]
then
   echo "Local $BRANCH is not up to date. "
   echo "Aborting."
   exit -1
fi

# check if tag to create has already been created
WORKING_DIR=`dirname $0`
VERSION=`python setup.py --version`
EXISTS=`git tag | grep $VERSION`

if [ "$VERSION" == "$EXISTS" ]
then
   echo "Revision $VERSION already tagged."
   echo "Aborting."
   exit -1
fi

# check if VERSION is in head of CHANGES.rst
REV_NOTE=`grep "[0-9/]\{10\} $VERSION" CHANGES.rst`
if [ -z "$REV_NOTE" ]
then
    echo "No notes for revision $VERSION found in CHANGES.rst"
    echo "Aborting."
    exit -1
fi

echo "Creating tag $VERSION..."
git tag -a "$VERSION" -m "Tag release for revision $VERSION"
git push --tags
echo "Done."
