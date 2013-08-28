
from setuptools import setup
import crate 
import os


if os.path.isfile('README.rst'):
    readme = open('README.rst').read()
else:
    readme = ''

setup(
    name='crate',
    url='https://github.com/crate/crate-python',
    version=crate.__version__,
    author='Lovely Systems',
    author_email='office@lovelysystems.com',
    package_dir = {'':'src'},
    description=crate.__doc__.strip(),
    long_description=readme,
    platforms=['any'],
    packages=['crate'],
    extras_require = dict(
        test = ['zope.testrunner'],
        testing = ['lovely.testlayers', 'zc.customdoctests']),
    install_requires = [
        'requests']
)
