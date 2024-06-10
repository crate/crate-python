.. _data-types:

==========
Data types
==========

The data types of the :ref:`CrateDB DBAPI database API client <connect>`.

.. rubric:: Table of contents

.. contents::
   :local:

.. _data-types-db-api:

Database API client
===================

This section documents data types for the CrateDB :ref:`Database API client
<connect>`.

.. CAUTION::

    The CrateDB Database API client implementation is incomplete. For the time
    being, the client uses native Python types.

In general, types are mapped as follows:

============= ===========
CrateDB       Python
============= ===========
`boolean`__   `boolean`__
`string`__    `str`__
`int`__       `int`__
`long`__      `int`__
`short`__     `int`__
`double`__    `float`__

`float`__     `float`__
`byte`__      `int`__
`geo_point`__ `list`__
`geo_shape`__ `dict`__
`object`__    `dict`__
`array`__     `list`__
============= ===========

__ https://crate.io/docs/crate/reference/en/latest/general/ddl/data-types.html#boolean
__ https://docs.python.org/3/library/stdtypes.html#boolean-type-bool
__ https://crate.io/docs/crate/reference/en/latest/general/ddl/data-types.html#character-data
__ https://docs.python.org/3/library/stdtypes.html#str
__ https://crate.io/docs/crate/reference/en/latest/general/ddl/data-types.html#numeric-data
__ https://docs.python.org/3/library/functions.html#int
__ https://crate.io/docs/crate/reference/en/latest/general/ddl/data-types.html#numeric-data
__ https://docs.python.org/3/library/functions.html#int
__ https://crate.io/docs/crate/reference/en/latest/general/ddl/data-types.html#numeric-data
__ https://docs.python.org/3/library/functions.html#int
__ https://crate.io/docs/crate/reference/en/latest/general/ddl/data-types.html#numeric-data
__ https://docs.python.org/3/library/functions.html#float
__ https://crate.io/docs/crate/reference/en/latest/general/ddl/data-types.html#numeric-data
__ https://docs.python.org/3/library/functions.html#float
__ https://crate.io/docs/crate/reference/en/latest/general/ddl/data-types.html#numeric-data
__ https://docs.python.org/3/library/functions.html#int
__ https://crate.io/docs/crate/reference/en/latest/general/ddl/data-types.html#geo-point
__ https://docs.python.org/3/library/stdtypes.html#list
__ https://crate.io/docs/crate/reference/en/latest/general/ddl/data-types.html#geo-shape
__ https://docs.python.org/3/library/stdtypes.html#dict
__ https://crate.io/docs/crate/reference/en/latest/general/ddl/data-types.html#object
__ https://docs.python.org/3/library/stdtypes.html#dict
__ https://crate.io/docs/crate/reference/en/latest/general/ddl/data-types.html#array
__ https://docs.python.org/3/library/stdtypes.html#list

When writing to CrateDB, the following conversions take place:

============= ====================================
Python        CrateDB
============= ====================================
`Decimal`__   `string`__
`date`__      `integer`__, `long`__, or `string`__
`datetime`__  `integer`__, `long`__, or `string`__
============= ====================================

__ https://docs.python.org/3/library/decimal.html
__ https://crate.io/docs/crate/reference/en/latest/general/ddl/data-types.html#character-data
__ https://docs.python.org/3/library/datetime.html#date-objects
__ https://crate.io/docs/crate/reference/en/latest/general/ddl/data-types.html#numeric-data
__ https://crate.io/docs/crate/reference/en/latest/general/ddl/data-types.html#numeric-data
__ https://crate.io/docs/crate/reference/en/latest/general/ddl/data-types.html#character-data
__ https://docs.python.org/3/library/datetime.html#datetime-objects
__ https://crate.io/docs/crate/reference/en/latest/general/ddl/data-types.html#numeric-data
__ https://crate.io/docs/crate/reference/en/latest/general/ddl/data-types.html#numeric-data
__ https://crate.io/docs/crate/reference/en/latest/general/ddl/data-types.html#character-data

.. NOTE::

    The type that ``date`` and ``datetime`` objects are mapped to, depends on the
    CrateDB column type.

.. NOTE::

    When using ``date`` or ``datetime`` objects with ``timezone`` information,
    the value is implicitly converted to a `Unix time`_ (epoch) timestamp, i.e.
    the number of seconds which have passed since 00:00:00 UTC on
    Thursday, 1 January 1970.

    This means, when inserting or updating records using timezone-aware Python
    ``date`` or ``datetime`` objects, timezone information will not be
    preserved. If you need to store it, you will need to use a separate column.


.. _Unix time: https://en.wikipedia.org/wiki/Unix_time
