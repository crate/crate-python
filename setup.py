
from setuptools import setup, find_packages
import os


def read(path):
    return open(os.path.join(os.path.dirname(__file__), path)).read()

long_description = (
    read('README.rst')
    + '\n' +
    read('src/crate/client/index.txt')
)

# import VERSION
execfile("src/crate/client/__version__.py")

setup(
    name='crate',
    version=VERSION,
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
    namespace_packages = ['crate'],
    extras_require=dict(
        test=['lovely.testlayers']
    ),
    install_requires=[
        'requests'
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
