# ibfoamrig

**Immersed Boundary Foam Rig** is a Python library for managing and post-processing
OpenFOAM cases. It was built to verify and validate the
[OpenHFDIB-RANS](https://github.com/LucieKubickova/openHFDIBRANS) solver, which
combines the hybrid fictitious domain–immersed boundary method (HFDIB) with
Reynolds-averaged turbulence models, against body-fitted reference solutions
such as `simpleFoam`.

## Installation

Requires Python 3.12 or newer.

```bash
pip install ibfoamrig
# or
pip install git+https://github.com/vecerniv/ibfoamrig.git
```

## Documentation

See the [documentation](https://vecerniv.github.io/ibfoamrig).

## License

[LGPL-2.1](LICENSE)
