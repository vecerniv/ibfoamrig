"""Sphinx configuration for the ibfoamrig documentation."""

from importlib.metadata import version as _version

from docutils import nodes
import polars as pl
from sphinx.ext.intersphinx import missing_reference as _intersphinx_ref

for _cls in (pl.DataFrame, pl.Series):
    _cls.__module__ = "polars"

_POLARS_URL = "https://docs.pola.rs/api/python/stable/"
_POLARS_PAGES = {
    "polars.DataFrame": "reference/dataframe/index.html",
    "polars.Series": "reference/series/index.html",
}

# -- Project -----------------------------------------------------------------
project = "ibfoamrig"
author = "eriazen"
copyright = f"2025-2026, {author}"
release = _version("ibfoamrig")
version = ".".join(release.split(".")[:2])

# -- General -----------------------------------------------------------------
extensions = [
    "sphinx.ext.autodoc",
    "sphinx.ext.autosummary",
    "sphinx.ext.napoleon",
    "sphinx.ext.intersphinx",
    "sphinx.ext.viewcode",
    "myst_parser",
    "sphinx_copybutton",
    "sphinx_design",
]
source_suffix = {".rst": "restructuredtext", ".md": "markdown"}
templates_path = ["_templates"]
exclude_patterns = ["_build"]

default_role = "py:obj"
nitpicky = True  # warn about every unresolved reference
nitpick_ignore = [
    ("py:class", "T"),
]
nitpick_ignore_regex = [
    ("py:class", r"numpy\._typing\..*"),
]

# -- Autodoc configuration ---------------------------------------------------
autosummary_generate = True
autosummary_ignore_module_all = False
autodoc_member_order = "bysource"
autodoc_typehints = "description"
autodoc_typehints_description_target = "documented_params"
autodoc_preserve_defaults = True

napoleon_google_docstring = True
napoleon_numpy_docstring = False
napoleon_include_init_with_doc = False
napoleon_use_rtype = False
napoleon_use_ivar = True

intersphinx_mapping = {
    "python": ("https://docs.python.org/3", None),
    "numpy": ("https://numpy.org/doc/stable/", None),
    "scipy": ("https://docs.scipy.org/doc/scipy/", None),
    "matplotlib": ("https://matplotlib.org/stable/", None),
    "polars": ("https://docs.pola.rs/api/python/stable/", None),
}


def _resolve_polars(app, env, node, contnode):
    """Links polars classes that are missing from the polars inventory."""
    page = _POLARS_PAGES.get(node.get("reftarget"))
    if page is None:
        return None
    ref = nodes.reference(
        "",
        "",
        internal=False,
        refuri=_POLARS_URL + page,
        reftitle=node["reftarget"],
    )
    ref.append(contnode)
    return ref


def _resolve_external(app, env, node, contnode):
    """Retries failed Python references with public names and any object type."""
    if node.get("refdomain") != "py" or node.get("reftype") == "obj":
        return None
    node["reftype"] = "obj"
    return _intersphinx_ref(app, env, node, contnode)


def _public_bases(bases):
    """Replaces private base classes with their own public bases."""
    out = []
    for base in bases:
        if getattr(base, "__name__", "").startswith("_"):
            out.extend(_public_bases(list(base.__bases__)))
        else:
            out.append(base)
    return out or [object]


def _hide_private_bases(app, name, obj, options, bases):
    bases[:] = _public_bases(bases)


def setup(app):
    app.connect("missing-reference", _resolve_polars)
    app.connect("missing-reference", _resolve_external)
    app.connect("autodoc-process-bases", _hide_private_bases)


# -- HTML --------------------------------------------------------------------
html_theme = "pydata_sphinx_theme"
html_title = f"ibfoamrig {release}"
html_show_sourcelink = False
html_theme_options = {
    "github_url": "https://github.com/vecerniv/ibfoamrig",
    "icon_links": [
        {
            "name": "PyPI",
            "url": "https://pypi.org/project/ibfoamrig/",
            "icon": "fa-brands fa-python",
        },
    ],
    "use_edit_page_button": True,
    "show_toc_level": 2,
    "footer_start": ["copyright"],
    "footer_end": ["sphinx-version", "theme-version"],
}
html_context = {
    "github_user": "vecerniv",
    "github_repo": "ibfoamrig",
    "github_version": "main",
    "doc_path": "docs",
}

# -- MyST --------------------------------------------------------------------
myst_enable_extensions = ["colon_fence", "deflist"]
