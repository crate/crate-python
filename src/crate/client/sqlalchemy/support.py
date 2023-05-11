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
import logging


logger = logging.getLogger(__name__)


def insert_bulk(pd_table, conn, keys, data_iter):
    """
    Use CrateDB's "bulk operations" endpoint as a fast path for pandas' and Dask's `to_sql()` [1] method.

    The idea is to break out of SQLAlchemy, compile the insert statement, and use the raw
    DBAPI connection client, in order to invoke a request using `bulk_parameters` [2]::

        cursor.execute(sql=sql, bulk_parameters=data)

    The vanilla implementation, used by SQLAlchemy, is::

        data = [dict(zip(keys, row)) for row in data_iter]
        conn.execute(pd_table.table.insert(), data)

    Batch chunking will happen outside of this function, for example [3] demonstrates
    the relevant code in `pandas.io.sql`.

    [1] https://pandas.pydata.org/docs/reference/api/pandas.DataFrame.to_sql.html
    [2] https://crate.io/docs/crate/reference/en/latest/interfaces/http.html#bulk-operations
    [3] https://github.com/pandas-dev/pandas/blob/v2.0.1/pandas/io/sql.py#L1011-L1027
    """

    # Compile SQL statement and materialize batch.
    sql = str(pd_table.table.insert().compile(bind=conn))
    data = list(data_iter)

    # For debugging and tracing the batches running through this method.
    if logger.level == logging.DEBUG:
        logger.debug(f"Bulk SQL:     {sql}")
        logger.debug(f"Bulk records: {len(data)}")
        # logger.debug(f"Bulk data:    {data}")

    # Invoke bulk insert operation.
    cursor = conn._dbapi_connection.cursor()
    cursor.execute(sql=sql, bulk_parameters=data)
    cursor.close()
