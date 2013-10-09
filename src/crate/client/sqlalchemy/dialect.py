
from __future__ import absolute_import
import logging
from datetime import datetime, date

from sqlalchemy.engine import default
from sqlalchemy import types as sqltypes

from .compiler import CrateCompiler


log = logging.getLogger(__name__)


class Date(sqltypes.Date):
    def bind_processor(self, dialect):
        def process(value):
            if value is not None:
                assert isinstance(value, date)
                return value.strftime('%Y-%m-%d')
        return process

    def result_processor(self, dialect, coltype):
        def process(value):
            if value:
                try:
                    return datetime.strptime(value, '%Y-%m-%d')
                except ValueError:
                    # Crate doesn't really have datetime or date types but a
                    # timestamp type. The "date" format itself isn't
                    # necessarily enforced (at least as of 0.14.0). If another
                    # client inserts a value that does contain time information
                    # it will be stored and returned on future requests.
                    log.warning('Received datetime but expected date')
                    return datetime.strptime(value, '%Y-%m-%dT%H:%M:%S.%fZ')
        return process


class DateTime(sqltypes.DateTime):
    def bind_processor(self, dialect):
        def process(value):
            if value is not None:
                assert isinstance(value, datetime)
                return value.strftime('%Y-%m-%dT%H:%M:%S.%fZ')
            return value
        return process

    def result_processor(self, dialect, coltype):
        def process(value):
            if value:
                return datetime.strptime(value, '%Y-%m-%dT%H:%M:%S.%fZ')
        return process


colspecs = {
    sqltypes.DateTime: DateTime,
    sqltypes.Date: Date
}


class CrateDialect(default.DefaultDialect):
    name = 'crate'
    statement_compiler = CrateCompiler
    colspecs = colspecs

    def __init__(self, *args, **kwargs):
        super(CrateDialect, self).__init__(*args, **kwargs)

        # currently our sql parser doesn't support unquoted column names that
        # start with _. Adding it here causes sqlalchemy to quote such columns
        self.identifier_preparer.illegal_initial_characters.add('_')

    def initialize(self, connection):
        # the DefaultDialect issues some queries to test for unicode support in
        # the resutls. etc. -> don't need any of that.
        pass

    def do_rollback(self, connection):
        # if any exception is raised by the dbapi, sqlalchemy by default
        # attempts to do a rollback crate doesn't support rollbacks.
        # implementing this as noop seems to cause sqlalchemy to propagate the
        # original exception to the user
        pass

    def connect(self, host=None, port=None, *args, **kwargs):
        server = None
        if host:
            server = '{0}:{1}'.format(host, port or '9200')
        if 'servers' in kwargs:
            server = kwargs.pop('servers')
        if server:
            return self.dbapi.connect(servers=server, **kwargs)
        return self.dbapi.connect(**kwargs)

    @classmethod
    def dbapi(cls):
        from crate import client
        return client
