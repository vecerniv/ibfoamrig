# lutils

**Lambda Utilities** is a Python library for managing and post-processing
OpenFOAM cases. It was built to verify and validate the
[OpenHFDIB-RANS](https://github.com/LucieKubickova/openHFDIBRANS) solver, which
combines the hybrid fictitious domain–immersed boundary method (HFDIB) with
Reynolds-averaged turbulence models, against body-fitted reference solutions
such as `simpleFoam`.

## Installation

Requires Python 3.12 or newer.

```bash
uv add git+https://github.com/vecerniv/lutils.git
# or
pip install git+https://github.com/vecerniv/lutils.git
```

## Documentation

See the [documentation](https://vecerniv.github.io/lutils).

## License

[LGPL-2.1](LICENSE)
