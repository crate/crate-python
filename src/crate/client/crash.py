"""
crate cli

can be used to query crate using SQL
"""
import inspect

import os
import sys
import select
import readline


assert readline  # imported so that cmd gains history-editing functionality
from cmd import Cmd
from argparse import ArgumentParser
from time import time

from prettytable import PrettyTable
from crate import client
from crate.client.exceptions import ConnectionError, Error, Warning
from crate.client.compat import raw_input


class CrateCmd(Cmd):
    prompt = 'cr> '
    line_delimiter = ';'
    multi_line_prompt = '... '
    NULL = "NULL"

    keywords = ["table", "index",
                "from", "into", "where", "values", "and", "or", "set", "with", "by", "using"
                "integer", "string", "float", "double", "short", "long", "byte", "timestamp",
                "replicas", "clustered"]

    def __init__(self, stdin=None, stdout=None):
        Cmd.__init__(self, "tab", stdin, stdout)
        self.conn = client.connect()
        self.cursor = self.conn.cursor()
        self.partial_lines = []

    def do_connect(self, server):
        """connect to one or more server with "connect servername:port" """
        time_start = time()
        self.conn = client.connect(server)
        self.cursor = self.conn.cursor()
        duration = time()-time_start
        self.print_success("connect", duration)

    def execute_query(self, statement):
        duration = self.execute(statement)
        if duration:
            self.pprint(self.cursor.fetchall())
            self.print_rows_selected(self.cursor.rowcount, duration)

    def execute(self, statement):
        try:
            time_start = time()
            self.cursor.execute(statement)
            duration = time()-time_start
            return duration
        except ConnectionError:
            print(
                'Use "connect <hostname:port>" to connect to a server first')
        except (Error, Warning) as e:
            if hasattr(e, 'message'):
                print(e.message)
            else:
                print(e)
        return False

    def pprint(self, rows):
        cols = self.cols()
        table = PrettyTable(cols)
        for col in cols:
            table.align[col] = "l"
        for row in rows:
            table.add_row(map(self._transform_field, row))
        print(table)

    def _transform_field(self, field):
        """transform field for displaying"""
        if field is None:
            return self.NULL
        else:
            return field

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
            "insert into locations (name) values ('Algol')"
        """
        duration = self.execute('insert ' + statement)
        if duration:
            self.print_rows_affected("insert", self.cursor.rowcount, duration)

    def do_delete(self, statement):
        """execute a SQL delete statement

        E.g.:
            "delete from locations where name = 'Algol'"
        """
        duration = self.execute('delete ' + statement)
        if duration:
            self.print_rows_affected("delete", self.cursor.rowcount, duration)

    def do_update(self, statement):
        """execute a SQL update statement

        E.g.:
            "update from locations set name = 'newName' where name = 'Algol'"
        """
        duration = self.execute('update ' + statement)
        if duration:
            self.print_rows_affected("update", self.cursor.rowcount, duration)

    def do_create(self, statement):
        """execute a SQL create statement

        E.g.:
            "create table locations (id integer, name string)"
        """
        duration = self.execute('create ' + statement)
        if duration:
            self.print_success("create", duration)


    def do_crate(self, statement):
        """alias for ``do_create``"""
        self.do_create(statement)

    def do_drop(self, statement):
        """execute a SQL drop statement

        E.g.:
            "drop table locations"
        """
        duration = self.execute('drop ' + statement)
        if duration:
            self.print_success("drop", duration)

    def do_exit(self, *args):
        """exit the shell"""
        self.stdout.write("Bye\n")
        sys.exit(0)

    def do_quit(self, *args):
        """exit the shell"""
        self.stdout.write("Bye\n")
        sys.exit(0)

    do_EOF = do_exit

    def print_rows_affected(self, command, rowcount=0, duration=0.00):
        """print success status with rows affected and query duration"""
        print("{0} OK, {1} row{2} affected ({3:.2f} sec)".format(
            command.upper(), rowcount, "s"[rowcount==1:], duration))

    def print_rows_selected(self, rowcount=0, duration=0.00):
        """print count of rows in result set and query duration"""
        print("SELECT {0} row{1} in set ({2:.2f} sec)".format(
            rowcount, "s"[rowcount==1:], duration))

    def print_success(self, command, duration=0.00):
        """print success status only and duration"""
        print("{0} OK ({1:.2f} sec)".format(command.upper(), duration))

    def cmdloop(self, intro=None):
        """Repeatedly issue a prompt, accept input, parse an initial prefix
        off the received input, and dispatch to action methods, passing them
        the remainder of the line as argument.

        """

        self.preloop()
        if self.use_rawinput and self.completekey:
            try:
                import rlcompleter
                self.old_completer = readline.get_completer()
                readline.set_completer(self.complete)
                if 'libedit' in readline.__doc__:
                    readline.parse_and_bind("bind ^I rl_complete")
                else:
                    readline.parse_and_bind("tab: complete")
            except ImportError:
                pass
        try:
            if intro is not None:
                self.intro = intro
            if self.intro:
                self.stdout.write(str(self.intro)+"\n")
            stop = None
            prompt = self.prompt
            while not stop:
                if self.cmdqueue:
                    line = self.cmdqueue.pop(0)
                else:
                    if self.use_rawinput:
                        try:
                            line = raw_input(prompt)
                        except EOFError:
                            line = 'EOF'
                    else:
                        self.stdout.write(prompt)
                        self.stdout.flush()
                        line = self.stdin.readline()
                        if not len(line):
                            line = 'EOF'
                        else:
                            line = line.rstrip('\r\n')
                    if (line or self.partial_lines) and line != 'EOF':
                        if line[-1:] != self.line_delimiter:
                            self.partial_lines.append(line)
                            prompt = self.multi_line_prompt
                        else:
                            self.partial_lines.append(line.rstrip(self.line_delimiter))
                            line = " ".join(self.partial_lines)
                            self.partial_lines = []
                            prompt = self.prompt
                if not self.partial_lines or line == 'EOF':
                    line = self.precmd(line)
                    stop = self.onecmd(line)
                    stop = self.postcmd(stop, line)
            self.postloop()
        finally:
            if self.use_rawinput and self.completekey:
                try:
                    readline.set_completer(self.old_completer)
                except ImportError:
                    pass

    def completedefault(self, text, line, begidx, endidx):
        """Method called to complete an input line when no command-specific
        complete_*() method is available.

        """
        mline = line.split(' ')[-1]
        offs = len(mline) - len(text)
        return [s[offs:] for s in self.keywords if s.startswith(mline)]

    def emptyline(self):
        """Called when an empty line is entered in response to the prompt.
        """
        pass

# uppercase commands
for name, attr in inspect.getmembers(CrateCmd, lambda attr: inspect.ismethod(attr)):
    if name.startswith("do_"):
        cmd_name = name.split("do_")[-1]
        setattr(CrateCmd, "do_{0}".format(cmd_name.upper()), attr)


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
