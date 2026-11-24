"""Sphinx configuration for the ibfoamrig documentation."""

from importlib.metadata import version as _version

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
    ("py:class", "ibfoamrig._typing.StrPath"),
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

intersphinx_mapping = {
    "python": ("https://docs.python.org/3", None),
    "numpy": ("https://numpy.org/doc/stable/", None),
    "scipy": ("https://docs.scipy.org/doc/scipy/", None),
    "matplotlib": ("https://matplotlib.org/stable/", None),
    "polars": ("https://docs.pola.rs/api/python/stable/", None),
}

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
