"""
About
=====

Example program to demonstrate efficient batched inserts using CrateDB and
pandas, based on SQLAlchemy's `insertmanyvalues` and CrateDB's bulk import
HTTP endpoint.

- https://docs.sqlalchemy.org/core/connections.html#controlling-the-batch-size
- https://crate.io/docs/crate/reference/en/latest/interfaces/http.html#bulk-operations


Setup
=====
::

    pip install --upgrade click colorlog crate pandas sqlalchemy


Synopsis
========
::

    # Run CrateDB.
    docker run --rm -it --publish=4200:4200 crate

    # Use local CrateDB.
    time python insert_pandas.py

    # Use local CrateDB with "basic" mode.
    time python insert_pandas.py --mode=basic --insertmanyvalues-page-size=5000

    # Use local CrateDB with "bulk" mode, and a few more records.
    time python insert_pandas.py --mode=bulk --bulk-size=20000 --num-records=75000

    # Use CrateDB Cloud.
    time python insert_pandas.py --dburi='crate://admin:<PASSWORD>@example.aks1.westeurope.azure.cratedb.net:4200?ssl=true'


Details
=======
To watch the HTTP traffic to your local CrateDB instance, invoke::

    sudo ngrep -d lo0 -Wbyline port 4200

"""
import logging

import click
import colorlog
import pkg_resources
import sqlalchemy as sa
from colorlog.escape_codes import escape_codes
from pandas._testing import makeTimeDataFrame

logger = logging.getLogger(__name__)

pkg_resources.require("sqlalchemy>=2.0")

SQLALCHEMY_LOGGING = True


class DatabaseWorkload:
    
    table_name = "foo"

    def __init__(self, dburi: str):
        self.dburi = dburi

    def get_engine(self, **kwargs):
        return sa.create_engine(self.dburi, **kwargs)

    def process(self, mode: str, num_records: int, bulk_size: int, insertmanyvalues_page_size: int):
        """
        Exercise different insert methods of pandas, SQLAlchemy, and CrateDB.
        """

        logger.info(f"Creating DataFrame with {num_records} records")

        # Create a DataFrame to feed into the database.
        df = makeTimeDataFrame(nper=num_records, freq="S")
        print(df)

        logger.info(f"Connecting to {self.dburi}")
        logger.info(f"Importing data with mode={mode}, bulk_size={bulk_size}, insertmanyvalues_page_size={insertmanyvalues_page_size}")

        engine = self.get_engine(insertmanyvalues_page_size=insertmanyvalues_page_size)

        # SQLAlchemy "Insert Many Values" mode. 40K records/s
        # https://docs.sqlalchemy.org/en/20/core/connections.html#engine-insertmanyvalues
        # https://docs.sqlalchemy.org/en/20/core/connections.html#engine-insertmanyvalues-page-size
        if mode == "basic":
            # Using `chunksize` does not make much of a difference here,
            # because chunking will be done by SQLAlchemy already.
            df.to_sql(name=self.table_name, con=engine, if_exists="replace", index=False)
            # df.to_sql(name=self.table_name, con=engine, if_exists="replace", index=False, chunksize=bulk_size)

        # Multi-row mode. It is slower.
        # https://pandas.pydata.org/docs/reference/api/pandas.DataFrame.to_sql.html
        elif mode == "multi":
            df.to_sql(name=self.table_name, con=engine, if_exists="replace", index=False, chunksize=bulk_size, method="multi")

        # CrateDB bulk transfer mode. 65K records/s
        # https://crate.io/docs/crate/reference/en/latest/interfaces/http.html#bulk-operations
        elif mode == "bulk":
            df.to_sql(name=self.table_name, con=engine, if_exists="append", index=False, chunksize=bulk_size, method=self.insert_bulk)

        else:
            raise ValueError(f"Unknown mode: {mode}")

    @staticmethod
    def insert_bulk(pd_table, conn, keys, data_iter):
        """
        A fast insert method for pandas and Dask, using CrateDB's "bulk operations" endpoint.

        The idea is to break out of SQLAlchemy, compile the insert statement, and use the raw
        DBAPI connection client, in order to invoke a request using `bulk_parameters`::

            cursor.execute(sql=sql, bulk_parameters=data)

        - https://crate.io/docs/crate/reference/en/latest/interfaces/http.html#bulk-operations

        The vanilla implementation, used by SQLAlchemy, is::

            data = [dict(zip(keys, row)) for row in data_iter]
            conn.execute(pd_table.table.insert(), data)

        """

        # Bulk
        sql = str(pd_table.table.insert().compile(bind=conn))
        data = list(data_iter)

        logger.info(f"Bulk SQL:     {sql}")
        logger.info(f"Bulk records: {len(data)}")

        cursor = conn._dbapi_connection.cursor()
        cursor.execute(sql=sql, bulk_parameters=data)
        cursor.close()

    def show_table_stats(self):
        """
        Display number of records in table.
        """
        engine = self.get_engine()
        with engine.connect() as conn:
            conn.exec_driver_sql(f"REFRESH TABLE {self.table_name};")
            result = conn.exec_driver_sql(f"SELECT COUNT(*) FROM {self.table_name};")
            table_size = result.scalar_one()
            logger.info(f"Table size: {table_size}")
        #engine.dispose()


def setup_logging(level=logging.INFO):
    reset = escape_codes["reset"]
    log_format = f"%(asctime)-15s [%(name)-26s] %(log_color)s%(levelname)-8s:{reset} %(message)s"

    handler = colorlog.StreamHandler()
    handler.setFormatter(colorlog.ColoredFormatter(log_format))

    logging.basicConfig(format=log_format, level=level, handlers=[handler])

    # Enable SQLAlchemy logging.
    if SQLALCHEMY_LOGGING:
        logging.getLogger("sqlalchemy").setLevel(level)


@click.command()
@click.option("--dburi", type=str, default="crate://localhost:4200", required=False, help="SQLAlchemy database connection URI.")
@click.option("--mode", type=str, default="bulk", required=False, help="Insert mode. Choose one of basic, multi, bulk.")
@click.option("--num-records", type=int, default=23_000, required=False, help="Number of records to insert.")
@click.option("--bulk-size", type=int, default=5_000, required=False, help="Bulk size / chunk size.")
@click.option("--insertmanyvalues-page-size", type=int, default=1_000, required=False, help="Page size for SA's insertmanyvalues.")
@click.help_option()
def main(dburi: str, mode: str, num_records: int, bulk_size: int, insertmanyvalues_page_size: int):
    setup_logging()
    dbw = DatabaseWorkload(dburi=dburi)
    dbw.process(mode, num_records, bulk_size, insertmanyvalues_page_size)
    dbw.show_table_stats()


if __name__ == "__main__":
    main()
