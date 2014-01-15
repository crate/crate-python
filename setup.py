
from setuptools import setup, find_packages
import sys
import os
import re


requirements = [
    'requests>=2.0.1,<3.0',
    'PrettyTable>=0.7,<0.8',
    'appdirs>=1.2,<2.0',
    'six'
]

if (2, 6) == sys.version_info[:2]:
    requirements.append('argparse>=1.2.1')

if sys.platform == 'darwin':
    requirements.append('readline>=6.2.4.1')


def read(path):
    return open(os.path.join(os.path.dirname(__file__), path)).read()

long_description = (
    read('README.rst')
    + '\n' +
    read('docs/client.txt')
    + '\n' +
    read('docs/blobs.txt')
)

versionf_content = open("src/crate/client/__init__.py").read()
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
    author='Crate Technology GmbH',
    author_email='office@crate.io',
    package_dir={'': 'src'},
    description='Crate client',
    long_description=long_description,
    platforms=['any'],
    license='Apache License 2.0',
    keywords='crate db api',
    packages=find_packages('src'),
    namespace_packages=['crate'],
    entry_points={
        'console_scripts': [
            'crash = crate.client.crash:main',
        ],
        'sqlalchemy.dialects': [
            'crate = crate.client.sqlalchemy:CrateDialect'
        ]
    },
    extras_require=dict(
        test=['lovely.testlayers',
              'mock>=1.0.1',
              'zope.testing',
              'zc.customdoctests>=1.0.1'],
        sqlalchemy=['sqlalchemy>=0.8.2']
    ),
    install_requires=requirements,
    package_data={'': ['*.txt']},
    classifiers=[
        'Development Status :: 2 - Pre-Alpha',
        'Intended Audience :: Developers',
        'License :: OSI Approved :: Apache Software License',
        'Operating System :: OS Independent',
        'Programming Language :: Python',
        'Topic :: Database'
    ],
)
