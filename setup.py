
from setuptools import setup, find_packages
import os
import re


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
    author_email='office@crate-technology.com',
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
    },
    extras_require=dict(
        test=['lovely.testlayers',
              'mock',
              'zope.testing']
    ),
    install_requires=[
        'requests',
        'PrettyTable'
    ],
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
