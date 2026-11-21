"""Lambda Utilities: managing and post-processing OpenFOAM cases."""

from importlib.metadata import PackageNotFoundError
from importlib.metadata import version

try:
    __version__ = version("lutils")
except:
    __version__ = "0.0.0"

__all__ = [__version__]
