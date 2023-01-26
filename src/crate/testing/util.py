class ExtraAssertions:
    """
    Additional assert methods for unittest.

    - https://github.com/python/cpython/issues/71339
    - https://bugs.python.org/issue14819
    - https://bugs.python.org/file43047/extra_assertions.patch
    """

    def assertIsSubclass(self, cls, superclass, msg=None):
        try:
            r = issubclass(cls, superclass)
        except TypeError:
            if not isinstance(cls, type):
                self.fail(self._formatMessage(msg,
                          '%r is not a class' % (cls,)))
            raise
        if not r:
            self.fail(self._formatMessage(msg,
                      '%r is not a subclass of %r' % (cls, superclass)))
