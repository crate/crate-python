
from __future__ import absolute_import
from sqlalchemy.engine import default


class CrateDialect(default.DefaultDialect):
    name = 'crate'

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
        server = '{0}:{1}'.format(host or 'localhost', port or '9200')
        if 'servers' in kwargs:
            server = kwargs.pop('servers')
        return self.dbapi.connect(servers=server, **kwargs)

    @classmethod
    def dbapi(cls):
        from crate import client
        return client
