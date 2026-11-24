"""Lambda Utilities: managing and post-processing OpenFOAM cases.

Subpackages:

* `ibfoamrig.io`: readers for OpenFOAM field files and post-processing tables.
* `ibfoamrig.core`: cases, data containers, time directories and sampling.
* `ibfoamrig.plot`: plotting functions, imported separately to avoid loading
  matplotlib on headless machines, e.g.
  ``from ibfoamrig.plot import plot_profile``.
"""

from importlib.metadata import PackageNotFoundError
from importlib.metadata import version

from ibfoamrig.core import CaseManager
from ibfoamrig.core import FieldData
from ibfoamrig.core import FoamCase
from ibfoamrig.core import InterpolationData
from ibfoamrig.core import ResidualData
from ibfoamrig.core import Sampler
from ibfoamrig.exceptions import IbfoamrigError

try:
    __version__ = version("ibfoamrig")
except PackageNotFoundError:
    __version__ = "0.0.0"

__all__ = [
    "CaseManager",
    "FieldData",
    "FoamCase",
    "InterpolationData",
    "IbfoamrigError",
    "ResidualData",
    "Sampler",
    "__version__",
]
