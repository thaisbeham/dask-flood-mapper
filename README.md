## Dask based Flood Mapping

This repository contains notebooks that explains how microwave backscattering can be used to map the extent of a flood. We replicate in this exercise the work of Bauer-Marschallinger et al. (2022) on the TU Wien Bayesian-based flood mapping algorithm. This workflow is entirely based on `Dask` and data access via [STAC](https://stacspec.org/en).

## Getting started 
### Usage

Inside the notebooks directory, you can find the implementation using a python module at **01_local_dask.ipynb**, which allows the calculations to be carried out by simply insierting in one function the bounding box and the time rang. The second notebook, **02_flood_map_decomposed.ipynb**, demonstrated each step of the whole workflow.

### Setup 

To run the workflow, clone the repository and install the dependencies by running the following at the terminal.

```sh 
git clone git@git.geo.tuwien.ac.at:mschobbe/dask-flood-mapper.git
cd dask-flood-mapper
pip install .
```

## Contact 
