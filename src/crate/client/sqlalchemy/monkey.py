from crate.client.sqlalchemy.sa_version import SA_VERSION, SA_1_4


def sqlalchemy_without_cresultproxy():
    """
    When running on SQLAlchemy 1.4 with the overhauled ``cresultproxy``
    C-implementation, UPDATE statements will raise::

        RuntimeError: number of values in row (3) differ from number of column processors (2)

    The problem can be reproduced by running::

        ./bin/test --test test_assign_to_craty_type_after_commit

    This function is a workaround to purge the ``cresultproxy``
    extension at runtime by using monkeypatching.

    The reason might be the CrateDB-specific amendments within
    ``visit_update_14`` or even general problems with the new
    architecture of SQLAlchemy 1.4 vs. the needs of CrateDB.

    See also:
    - https://docs.sqlalchemy.org/en/14/changelog/migration_14.html#rowproxy-is-no-longer-a-proxy-is-now-called-row-and-behaves-like-an-enhanced-named-tuple
    - https://github.com/sqlalchemy/sqlalchemy/blob/rel_1_4_0b1/lib/sqlalchemy/cextension/resultproxy.c
    """
    import sys

    # https://gist.github.com/schipiga/482de016fa749bc08c7b36cf5323fd1b
    to_uncache = []
    for mod in sys.modules:
        if mod.startswith("sqlalchemy"):
            to_uncache.append(mod)
    for mod in to_uncache:
        del sys.modules[mod]

    # Don't allow SQLAlchemy to bring in this extension again.
    sys.modules["sqlalchemy.cresultproxy"] = None


# FIXME: Workaround to be able to use SQLAlchemy 1.4.
#        Caveat: This purges the ``cresultproxy`` extension
#        at runtime, so it will impose a speed bump.
if SA_VERSION >= SA_1_4:
    sqlalchemy_without_cresultproxy()
