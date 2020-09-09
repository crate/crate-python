.. _getting-started:

===============
Getting started
===============

Learn how to install and get started the :ref:`CrateDB Python client library
<index>`.

.. rubric:: Table of contents

.. contents::
   :local:

Prerequisites
=============

Python 3.7 is recommended.

However, :ref:`older versions of Python <python-versions>` can still be used.

`Pip`_ should be installed on your system.

Install
=======

The CrateDB Python client is `available`_ as a `PyPI`_ package.

To install the package, run:

.. code-block:: sh

   sh$ pip install crate

After that is done, you can import the library, like so:

    >>> from crate import client

Interactive use
===============

Python provides a REPL_, also known as an interactive language shell. It's a
handy way to experiment with code and try out new libraries. We recommend
`iPython`_, which you can install, like so::

    sh$ pip install iPython

Once installed, you can start it up, like this::

    sh$ ipython

From there, try importing the CrateDB Python client library and seeing how far
you get with the built-in ``help()`` function (that can be called on any
object), iPython's autocompletion, and many other features.

.. SEEALSO::

   `The iPython Documentation`_

Set up as a dependency
======================

There are `many ways`_ to handle Python project dependencies. The official PyPI
package should be compatible with all of them.

Next steps
==========

Learn how to :ref:`connect to CrateDB <connect>`.

.. _available: https://pypi.python.org/pypi/pip
.. _iPython: https://ipython.org/
.. _many ways: https://packaging.python.org/key_projects/
.. _Pip: https://pip.pypa.io/en/stable/installing/
.. _PyPI: https://pypi.org/
.. _REPL: https://en.wikipedia.org/wiki/Read%E2%80%93eval%E2%80%93print_loop
.. _The iPython Documentation: https://ipython.readthedocs.io/en/stable/
