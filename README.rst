
.. image:: http://www.crate-technology.com/assets/img/logo.png
   :width: 155px
   :height: 45px
   :alt: Crate-Technology
   :target: http://www.crate-technology.com/

Overview
========

This is the database adapter for the crate database. Its main feature is a
implementation of the Python `DB API 2.0
<http://www.python.org/dev/peps/pep-0249/>`_ specification. Take a look at the
`client docs <docs/client.txt>`_ for usage information.

In addition the client library also exposes some features of crate like blob
support as a more convenient high level API since SQL isn't well suited to blob
handling. See `the blob docs <docs/blobs.txt>`_ for more details.

Installation
============

Installing via pip
------------------

To install the crate client via `pip <https://pypi.python.org/pypi/pip>`_ use
the following command::

    $ pip install crate

To update use::

    $ pip install -U crate

Installing via easy_install
---------------------------

If you prefer easy_install which is provided by
`setuptools <https://pypi.python.org/pypi/setuptools/1.1>`_
use the following command::

    $ easy_install crate

To update use::

    $ easy_install -U crate


License
=======

Copyright 2013 Crate-Technology GmbH

Licensed under the Apache License, Version 2.0 (the 'License');
you may not use this file except in compliance with the License.
You may obtain a copy of the License at

    http://www.apache.org/licenses/LICENSE-2.0

Unless required by applicable law or agreed to in writing, software
distributed under the License is distributed on an 'AS IS' BASIS,
WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
See the License for the specific language governing permissions and
limitations under the License.
