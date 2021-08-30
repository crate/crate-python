from crate.theme.rtd.conf.python import *


if "sphinx.ext.intersphinx" not in extensions:
    extensions += ["sphinx.ext.intersphinx"]


if "intersphinx_mapping" not in globals():
    intersphinx_mapping = {}


intersphinx_mapping.update({
    'reference': ('https://crate.io/docs/crate/reference/en/latest/', None),
    'sa': ('https://docs.sqlalchemy.org/en/13/', None),
    })


rst_prolog = """
.. |nbsp| unicode:: 0xA0
   :trim:
"""
