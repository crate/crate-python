# -*- coding: utf-8 -*-
from django.db.backends.creation import BaseDatabaseCreation


class DatabaseCreation(BaseDatabaseCreation):
    data_types = {
        'AutoField':                    'integer',
        #'BinaryField':                  'BLOB',
        'BooleanField':                 'boolean',
        'CharField':                    'string',
        'CommaSeparatedIntegerField':   'string',
        #'DateField':                    'timestamp',
        'DateTimeField':                'timestamp',
        #'DecimalField':                 'decimal',
        'FileField':                    'string',
        'FilePathField':                'string',
        'FloatField':                   'float',
        'IntegerField':                 'integer',
        'BigIntegerField':              'long',
        'IPAddressField':               'ip',
        'GenericIPAddressField':        'string',
        'NullBooleanField':             'boolean',
        'OneToOneField':                'integer',
        'PositiveIntegerField':         'integer',
        'PositiveSmallIntegerField':    'short',
        'SlugField':                    'string',
        'SmallIntegerField':            'short',
        'TextField':                    'string',
        #'TimeField':                    'long',
    }

    def sql_create_model(self, model, style, known_models=set()):
        """
        issue a CREATE TABLE statement from a model

        TODO: support additional fields

        :return: list of sql statements, {}
        """
        opts = model._meta
        if not opts.managed or opts.proxy or opts.swapped:
            return [], {}
        final_output = []
        table_output = []
        qn = self.connection.ops.quote_name
        for f in opts.local_fields:
            col_type = f.db_type(connection=self.connection)
            if col_type is None:
                # Skip ManyToManyFields, because they're not represented as
                # database columns in this table.
                continue

            # Make the definition (e.g. 'foo VARCHAR(30)') for this field.
            field_output = [style.SQL_FIELD(qn(f.column)),
                style.SQL_COLTYPE(col_type)]
            # Oracle treats the empty string ('') as null, so coerce the null
            # option whenever '' is a possible value.
            #null = f.null
            #if (f.empty_strings_allowed and not f.primary_key and
            #        self.connection.features.interprets_empty_strings_as_nulls):
            #    null = True
            #if not null:
            #    field_output.append(style.SQL_KEYWORD('NOT NULL'))
            if f.primary_key:
                field_output.append(style.SQL_KEYWORD('PRIMARY KEY'))
            #elif f.unique:
            #    field_output.append(style.SQL_KEYWORD('UNIQUE'))
            elif hasattr(f, "fulltext_index"):
                # TODO: support compound index
                fulltext_index = getattr(f, "fulltext_index", None)
                analyzer = getattr(f, "analyzer", None)
                if fulltext_index:
                    field_output.append(style.SQL_KEYWORD("INDEX USING FULLTEXT"))
                    if analyzer:
                        field_output.append(style.SQL_KEYWORD("WITH(analyzer='{}')".format(analyzer)))

            table_output.append(' '.join(field_output))

        full_statement = [style.SQL_KEYWORD('CREATE TABLE') + ' ' +
                          style.SQL_TABLE(qn(opts.db_table)) + ' (']
        for i, line in enumerate(table_output):  # Combine and add commas.
            full_statement.append(
                '    %s%s' % (line, ',' if i < len(table_output) - 1 else ''))
        full_statement.append(')')

        # CRATE TABLE PARAMS
        crate_table_params = []
        crate_opts = getattr(model, "Crate", None)
        if crate_opts:
            number_of_replicas = getattr(crate_opts, "number_of_replicas", None)
            clustered_by = getattr(crate_opts, "clustered_by", None)
            number_of_shards = getattr(crate_opts, "number_of_shards", None)
            if clustered_by is not None or number_of_shards is not None:
                crate_table_params.append('CLUSTERED')
                if clustered_by is not None:
                    crate_table_params.append('BY ({})'.format(qn(clustered_by)))
                if number_of_shards is not None:
                    crate_table_params.append('INTO {} SHARDS'.format(number_of_shards))
            if number_of_replicas is not None:
                crate_table_params.append('REPLICAS {}'.format(number_of_replicas))
            full_statement.append(' '.join(crate_table_params))

        final_output.append('\n'.join(full_statement))

        return final_output, {}

    def sql_for_inline_foreign_key_references(self, model, field, known_models, style):
        """FOREIGN KEY not supported"""
        return [], False

    def sql_for_pending_references(self, model, style, pending_references):
        """
        should create ALTER TABLE statements

        not supported
        """
        return []

    def sql_indexes_for_model(self, model, style):
        """
        should create CREATE INDEX statements

        not supported
        """
        return []

    def sql_indexes_for_field(self, model, f, style):
        """not supported"""
        return []

    def sql_indexes_for_fields(self, model, fields, style):
        """not supported"""
        return []

    def sql_destroy_model(self, model, references_to_delete, style):
        """DROP TABLE"""
        qn = self.connection.ops.quote_name
        return ['%s %;' % (style.SQL_KEYWORD('DROP TABLE'),
                              style.SQL_TABLE(qn(model._meta.db_table)))]

    def sql_remove_table_constraints(self, model, references_to_delete, style):
        """not supported"""
        return []

    def sql_destroy_indexes_for_model(self, model, style):
        """not supported"""
        return []

    def sql_destroy_indexes_for_field(self, model, f, style):
        """not supported"""
        return []

    def sql_destroy_indexes_for_fields(self, model, fields, style):
        """not supported"""
        return []

    def _create_test_db(self, verbosity, autoclobber):
        """cannot create dbs yet"""
        return ""

    def _destroy_test_db(self, test_database_name, verbosity):
        """cannot destroy dbs yet"""
