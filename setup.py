
from setuptools import setup
import os


def read(path):
    return open(os.path.join(os.path.dirname(__file__), path)).read()

long_description = (
    read('README.rst')
    + '\n' +
    read('src/crate/client/client.txt')
    + '\n')

packages = [
    'crate',
    'crate.client'
]

setup(
    name='crate',
    url='https://github.com/crate/crate-python',
    author='Lovely Systems',
    author_email='office@lovelysystems.com',
    package_dir={'': 'src'},
    description='Crate client',
    long_description=long_description,
    platforms=['any'],
    packages=packages,
    extras_require=dict(
        test=['lovely.testlayers']),
    install_requires=[
        'requests']
)
