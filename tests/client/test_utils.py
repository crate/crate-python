import os

from tests.client.utils import temp_env


def test_util_temp_env():
    """
    Verify that temp_env correctly injects and cleans up environment variables.
    """
    env = os.environ.copy()
    new_env_var = {'some_var': '1'}

    with temp_env(**new_env_var):
        # Assert that the difference of the two environs is the new variable.
        assert set(env.items()) ^ set(os.environ.items()) == set(new_env_var.items())

    # key should now not exist in the current imported os.environ.
    assert list(new_env_var.keys())[0] not in os.environ

    import importlib
    importlib.reload(os)

    # key should still not exist even when reloading the os module.
    assert list(new_env_var.keys())[0] not in os.environ