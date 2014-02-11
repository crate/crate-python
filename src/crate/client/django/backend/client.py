# -*- coding: utf-8 -*-
from django.db.backends import BaseDatabaseClient
from crate.client.crash import main as crash_main


class DatabaseClient(BaseDatabaseClient):
    executable_name = 'crash'

    def runshell(self):
        """TODO: run shell"""
        settings_dict = self.connection.settings_dict

        import sys
        sys.argv = [sys.argv[0], "--hosts", settings_dict['SERVERS']]
        crash_main()
