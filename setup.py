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

import os
import re

from setuptools import find_namespace_packages, setup


def read(path):
    with open(os.path.join(os.path.dirname(__file__), path)) as f:
        return f.read()


long_description = read("README.rst")
versionf_content = read("src/crate/client/__init__.py")
version_rex = r'^__version__ = [\'"]([^\'"]*)[\'"]$'
m = re.search(version_rex, versionf_content, re.M)
if m:
    version = m.group(1)
else:
    raise RuntimeError("Unable to find version string")

setup(
    name="crate",
    version=version,
    url="https://github.com/crate/crate-python",
    author="Crate.io",
    author_email="office@crate.io",
    description="CrateDB Python Client",
    long_description=long_description,
    long_description_content_type="text/x-rst",
    platforms=["any"],
    license="Apache License 2.0",
    keywords="cratedb db api dbapi database sql http rdbms olap",
    packages=find_namespace_packages("src"),
    package_dir={"": "src"},
    install_requires=[
        "orjson<4",
        "urllib3",
        "verlib2",
    ],
    extras_require={
        "doc": [
            "crate-docs-theme>=0.26.5",
            "sphinx>=3.5,<9",
        ],
        "test": [
            'backports.zoneinfo<1; python_version<"3.9"',
            "certifi",
            "createcoverage>=1,<2",
            "mypy<1.15",
            "poethepoet<0.33",
            "ruff<0.10",
            "stopit>=1.1.2,<2",
            "pytz",
            "zc.customdoctests>=1.0.1,<2",
            "zope.testing>=4,<6",
            "zope.testrunner>=5,<7",
        ],
    },
    python_requires=">=3.6",
    package_data={"": ["*.txt"]},
    classifiers=[
        "Development Status :: 5 - Production/Stable",
        "Intended Audience :: Developers",
        "License :: OSI Approved :: Apache Software License",
        "Operating System :: OS Independent",
        "Programming Language :: Python",
        "Programming Language :: Python :: 3",
        "Programming Language :: Python :: 3.6",
        "Programming Language :: Python :: 3.7",
        "Programming Language :: Python :: 3.8",
        "Programming Language :: Python :: 3.9",
        "Programming Language :: Python :: 3.10",
        "Programming Language :: Python :: 3.11",
        "Programming Language :: Python :: 3.12",
        "Programming Language :: Python :: 3.13",
        "Programming Language :: Python :: Implementation :: CPython",
        "Programming Language :: Python :: Implementation :: PyPy",
        "Topic :: Database",
    ],
)
