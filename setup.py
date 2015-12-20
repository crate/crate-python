# -*- coding: utf-8; -*-
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

from setuptools import setup, find_packages
import os
import re


requirements = [
    'setuptools',
    'urllib3',
    'six'
]


def read(path):
    with open(os.path.join(os.path.dirname(__file__), path)) as f:
        return f.read()


long_description = (
    read('README.rst') + '\n' +
    read('docs/client.txt') + '\n' +
    read('docs/blobs.txt')
)

versionf_content = read("src/crate/client/__init__.py")
version_rex = r'^__version__ = [\'"]([^\'"]*)[\'"]$'
m = re.search(version_rex, versionf_content, re.M)
if m:
    version = m.group(1)
else:
    raise RuntimeError('Unable to find version string')

setup(
    name='crate',
    version=version,
    url='https://github.com/crate/crate-python',
    author='CRATE Technology GmbH',
    author_email='office@crate.io',
    package_dir={'': 'src'},
    description='Crate Data Python client',
    long_description=long_description,
    platforms=['any'],
    license='Apache License 2.0',
    keywords='crate db api sqlalchemy',
    packages=find_packages('src'),
    namespace_packages=['crate'],
    entry_points={
        'sqlalchemy.dialects': [
            'crate = crate.client.sqlalchemy:CrateDialect'
        ]
    },
    extras_require=dict(
        test=['mock>=1.0.1',
              'zope.testing',
              'zc.customdoctests>=1.0.1'],
        sqlalchemy=['sqlalchemy>=0.8.2']
    ),
    install_requires=requirements,
    package_data={'': ['*.txt']},
    classifiers=[
        'Development Status :: 5 - Production/Stable',
        'Intended Audience :: Developers',
        'License :: OSI Approved :: Apache Software License',
        'Operating System :: OS Independent',
        'Programming Language :: Python',
        'Programming Language :: Python :: 2',
        'Programming Language :: Python :: 2.6',
        'Programming Language :: Python :: 2.7',
        'Programming Language :: Python :: 3',
        'Programming Language :: Python :: 3.3',
        'Programming Language :: Python :: 3.4',
        'Programming Language :: Python :: 3.5',
        'Programming Language :: Python :: Implementation :: CPython',
        'Programming Language :: Python :: Implementation :: PyPy',
        'Topic :: Database'
    ],
)
