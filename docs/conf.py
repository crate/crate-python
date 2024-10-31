# ruff: noqa: F403, F405
from crate.theme.rtd.conf.python import *

if "sphinx.ext.intersphinx" not in extensions:
    extensions += ["sphinx.ext.intersphinx"]


if "intersphinx_mapping" not in globals():
    intersphinx_mapping = {}


intersphinx_mapping.update(
    {
        "py": ("https://docs.python.org/3/", None),
        "urllib3": ("https://urllib3.readthedocs.io/en/1.26.13/", None),
    }
)


linkcheck_anchors = True
linkcheck_ignore = []

# Disable version chooser.
html_context.update(
    {
        "display_version": False,
        "current_version": None,
        "versions": [],
    }
)

rst_prolog = """
.. |nbsp| unicode:: 0xA0
   :trim:
"""
