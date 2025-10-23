import contextlib
import os


@contextlib.contextmanager
def temp_env(**environment_variables):
    """
    Context manager that sets temporal environment variables within the scope.

    Example:
        with temp_env(some_key='value'):
            import os
            'some_key' in os.environ
            # True
        'some_key' in os.environ
        # False
    """
    try:
        for k, v in environment_variables.items():
            os.environ[k] = str(v)
            yield
    finally:
        for k, v in environment_variables.items():
            os.unsetenv(k)
            del os.environ[k]