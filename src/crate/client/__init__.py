from .connection import connect
from .exceptions import Error

# version string read from setup.py using a regex. Take care not to break the
# regex!
__version__ = "0.0.6"

apilevel = "2.0"
threadsafety = 2
paramstyle = "qmark"
