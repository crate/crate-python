# -*- coding: utf-8 -*-
from django.db.backends import BaseDatabaseIntrospection


class DatabaseIntrospection(BaseDatabaseIntrospection):
    data_types_reverse = {
        "boolean": "BooleanField",
        "byte": "SmallIntegerField",
        "short": "SmallIntegerField",
        "integer": "IntegerField",
        "long": "BigIntegerField",
        "float": "FloatField",
        "double": "FloatField",  # no double type in python
        "timestamp": "DateTimeField",
        "ip": "CharField",
        "string": "CharField",
        # TODO: object
    }

    def get_table_list(self, cursor):
        """TODO"""
        tables = []
        cursor.execute(
            "select table_name from information_schema.tables "
            "where schema_name='doc'".format())
        for table_name in cursor.fetchall():
            if isinstance(table_name, list):
                table_name = table_name[0]
            tables.append(table_name)
        return tables

    def sequence_list(self):
        """sequences not supported"""
        return []

    def get_key_columns(self, cursor, table_name):
        return []

    def get_indexes(self, cursor, table_name):
        indexes = {}
        cursor.execute(
            "select constraint_name from information_schema.table_constraints "
            "where schema_name='doc' and table_name='{}'".format(table_name)
        )
        for colname in cursor.fetchall():
            if isinstance(colname, list):
                colname = colname[0]
            indexes[colname] = {
                'primary_key': True,
                'unique': True
            }
        return indexes
