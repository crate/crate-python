.. _getting-started:

===============
Getting started
===============

Learn how to install and get started with the Python client library for
`CrateDB`_.

.. rubric:: Table of contents

.. contents::
   :local:

Install
=======

.. highlight:: sh

The CrateDB Python client is available as package `crate`_ on `PyPI`_.

To install the most recent driver version, run::

    pip install --upgrade crate

After that is done, you can import the library, like so:

.. code-block:: python

    >>> from crate import client

Interactive use
===============

Python provides a REPL_, also known as an interactive language shell. It's a
handy way to experiment with code and try out new libraries. We recommend
`IPython`_, which you can install, like so::

    pip install ipython

Once installed, you can start it up, like this::

    ipython

From there, try importing the CrateDB Python client library and seeing how far
you get with the built-in ``help()`` function (that can be called on any
object), IPython's autocompletion, and many other features.

.. SEEALSO::

   `The IPython Documentation`_

Set up as a dependency
======================

There are `many ways`_ to add the ``crate`` package as a dependency to your
project. All of them work equally well. Please note that you may want to employ
package version pinning in order to keep the environment of your project stable
and reproducible, achieving `repeatable installations`_.


Next steps
==========

Learn how to :ref:`connect to CrateDB <connect>`.


.. _crate: https://pypi.org/project/crate/
.. _CrateDB: https://crate.io/products/cratedb/
.. _IPython: https://ipython.org/
.. _many ways: https://packaging.python.org/key_projects/
.. _PyPI: https://pypi.org/
.. _repeatable installations: https://pip.pypa.io/en/latest/topics/repeatable-installs/
.. _REPL: https://en.wikipedia.org/wiki/Read%E2%80%93eval%E2%80%93print_loop
.. _The IPython Documentation: https://ipython.readthedocs.io/
