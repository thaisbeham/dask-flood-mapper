## Dask based Flood Mapping

![CI](https://github.com/TUW-GEO/dask-flood-mapper/actions/workflows/pytest.yml/badge.svg)

This repository contains notebooks that explains how microwave backscattering can be used to map the extent of a flood. We replicate in this exercise the work of Bauer-Marschallinger et al. (2022) on the TU Wien Bayesian-based flood mapping algorithm. This workflow is entirely based on `Dask` and data access via [STAC](https://stacspec.org/en).

To run the workflow

```
git clone git@git.geo.tuwien.ac.at:mschobbe/dask-flood-mapper.git
cd dask-flood-mapper
pip install .
```
### Linter

Before each commiting, Ruff is actioned. To run Ruff without commiting, run:

```bash
pre-commit run --all-files
```

or

```bash
ruff check --fix --output-format concise
```

To fix the format, Ruff also offers this option with the command:

```bash
ruff format
```