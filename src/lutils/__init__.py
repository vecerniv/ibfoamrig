"""Lambda Utilities: managing and post-processing OpenFOAM cases.

Subpackages:

* `lutils.io`: readers for OpenFOAM field files and post-processing tables.
* `lutils.core`: cases, data containers, time directories and sampling.
* `lutils.plot`: plotting functions, imported separately to avoid loading
  matplotlib on headless machines, e.g.
  ``from lutils.plot import plot_profile``.
"""

from importlib.metadata import PackageNotFoundError
from importlib.metadata import version

from lutils.core import CaseManager
from lutils.core import FieldData
from lutils.core import FoamCase
from lutils.core import InterpolationData
from lutils.core import ResidualData
from lutils.core import Sampler
from lutils.exceptions import LutilsError

try:
    __version__ = version("lutils")
except PackageNotFoundError:
    __version__ = "0.0.0"

__all__ = [
    "CaseManager",
    "FieldData",
    "FoamCase",
    "InterpolationData",
    "LutilsError",
    "ResidualData",
    "Sampler",
    "__version__",
]
