# -*- coding: utf-8; -*-
import sys
import warnings
from unittest import TestCase, skipIf

from crate.client.sqlalchemy import SA_1_4, SA_VERSION
from crate.testing.util import ExtraAssertions


class SqlAlchemyWarningsTest(TestCase, ExtraAssertions):

    @skipIf(SA_VERSION >= SA_1_4, "There is no deprecation warning for "
                                  "SQLAlchemy 1.3 on higher versions")
    def test_sa13_deprecation_warning(self):
        """
        Verify that a `DeprecationWarning` is issued when running SQLAlchemy 1.3.

        https://docs.python.org/3/library/warnings.html#testing-warnings
        """
        with warnings.catch_warnings(record=True) as w:

            # Cause all warnings to always be triggered.
            warnings.simplefilter("always")

            # Trigger a warning by importing the SQLAlchemy dialect module.
            # Because it already has been loaded, unload it beforehand.
            del sys.modules["crate.client.sqlalchemy"]
            import crate.client.sqlalchemy  # noqa: F401

            # Verify details of the SA13 EOL/deprecation warning.
            self.assertEqual(len(w), 1)
            self.assertIsSubclass(w[-1].category, DeprecationWarning)
            self.assertIn("SQLAlchemy 1.3 is effectively EOL.", str(w[-1].message))
