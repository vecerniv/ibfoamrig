# ibfoamrig

**Immersed Boundary OpenFOAM Rig** is a Python library for managing and
post-processing OpenFOAM cases. It was built to verify and validate the
[OpenHFDIB-RANS](https://github.com/LucieKubickova/openHFDIBRANS) solver
against body-fitted reference solutions such as `simpleFoam`.

```bash
pip install ibfoamrig
```

```python
import ibfoamrig as ifr

case = ifr.FoamCase("path/to/case")
```

```{toctree}
:hidden:
:maxdepth: 2

api
```
