"""Cases, data containers, time directories and sampling.

* `FoamCase` and `CaseManager` locate files in one or several cases.
* `FieldData`, `ResidualData` and `InterpolationData` hold loaded data.
* `Sampler` interpolates cell values at arbitrary points.
"""

from ibfoamrig.core.case import FieldStats
from ibfoamrig.core.case import FoamCase
from ibfoamrig.core.data import FieldData
from ibfoamrig.core.data import InterpolationData
from ibfoamrig.core.data import ResidualData
from ibfoamrig.core.manager import CaseManager
from ibfoamrig.core.sampling import line_points
from ibfoamrig.core.sampling import Sampler
from ibfoamrig.core.time_dirs import find_time
from ibfoamrig.core.time_dirs import latest_time
from ibfoamrig.core.time_dirs import list_times
from ibfoamrig.core.time_dirs import TimeDirectory

__all__ = [
    "CaseManager",
    "FieldData",
    "FieldStats",
    "FoamCase",
    "InterpolationData",
    "ResidualData",
    "Sampler",
    "TimeDirectory",
    "find_time",
    "latest_time",
    "line_points",
    "list_times",
]
