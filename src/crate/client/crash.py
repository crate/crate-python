"""
crate cli

can be used to query crate using SQL
"""

import os
import sys
import select
import readline


assert readline  # imported so that cmd gains history-editing functionality
from cmd import Cmd
from argparse import ArgumentParser

from prettytable import PrettyTable
from crate import client
from crate.client.exceptions import ConnectionError
from requests.exceptions import HTTPError


class CrateCmd(Cmd):
    prompt = 'cr> '

    def __init__(self, *args):
        Cmd.__init__(self, *args)
        self.conn = client.connect()
        self.cursor = self.conn.cursor()

    def do_connect(self, server):
        """connect to one or more server with "connect servername:port" """
        self.conn = client.connect(server)
        self.cursor = self.conn.cursor()

    def execute_query(self, statement):
        if self.execute(statement):
            self.pprint(self.cursor.fetchall())

    def execute(self, statement):
        try:
            self.cursor.execute(statement)
            return True
        except ConnectionError:
            print(
                'Use "connect <hostname:port>" to connect to a server first')
        except HTTPError as e:
            print(e.response.json().get('error', ''))
        return False

    def pprint(self, rows):
        cols = self.cols()
        table = PrettyTable(cols)
        for col in cols:
            table.align[col] = "l"
        for row in rows:
            table.add_row(row)
        print(table)

    def cols(self):
        return [c[0] for c in self.cursor.description]

    def do_select(self, statement):
        """execute a SQL select statement

        E.g.:
            "select name from locations where name = 'Algol'"
        """
        self.execute_query('select ' + statement)

    def do_insert(self, statement):
        """execute a SQL insert statement

        E.g.:
            "insert into locations (name) values ('Algol')
        """
        self.execute('insert ' + statement)

    def do_delete(self, statement):
        """execute a SQL delete statement

        E.g.:
            "delete from locations where name = 'Algol'
        """
        self.execute('delete ' + statement)

    def do_exit(self, *args):
        """exit the shell"""
        sys.exit()

    def do_quit(self, *args):
        """exit the shell"""
        sys.exit()


def main():
    parser = ArgumentParser(description='crate shell')
    parser.add_argument('-v', '--verbose', action='count',
                        help='use -v to get debug output')
    parser.add_argument('-s', '--statement', type=str,
                        help='execute sql statement')
    parser.add_argument('--hosts', type=str,
                        help='connect to crate hosts')
    args = parser.parse_args()
    cmd = CrateCmd()
    if args.hosts:
        cmd.do_connect(args.hosts)

    # select.select on sys.stdin doesn't work on windows
    # so currently there is no pipe support
    if os.name == 'posix':
        # use select.select to check if input is available
        # otherwise sys.stdin would block
        while sys.stdin in select.select([sys.stdin], [], [], 0)[0]:
            line = sys.stdin.readline()
            if line:
                cmd.onecmd(line)
            else:
                sys.exit(0)

    if args.statement:
        cmd.onecmd(args.statement)
    else:
        cmd.cmdloop()


if __name__ == '__main__':
    main()
