# Dask based Flood Mapping

![CI](https://github.com/TUW-GEO/dask-flood-mapper/actions/workflows/pytest.yml/badge.svg)
[![DOI](https://zenodo.org/badge/859296745.svg)](https://doi.org/10.5281/zenodo.15004960)


Map floods with Sentinel-1 radar images. We replicate in this package the work of Bauer-Marschallinger et al. (2022)<sup>1</sup> on the TU Wien Bayesian-based flood mapping algorithm. This implementation is entirely based on [`dask`](https://www.dask.org/) and data access via [STAC](https://stacspec.org/en) with [`odc-stac`](https://odc-stac.readthedocs.io/en/latest/). The algorithm requires three pre-processed input datasets stored and accessible via STAC at the Earth Observation Data Centre For Water Resources Monitoring (EODC). It is foreseen that future implementations can also use data from other STAC catalogues. This notebook explains how microwave backscattering can be used to map the extent of a flood. The workflow detailed in this [notebook](https://tuw-geo.github.io/dask-flood-mapper/notebooks/03_flood_map.html) forms the backbone of this package. For a short overview of the Bayesian decision method for flood mapping see this [ProjectPythia book](https://projectpythia.org/eo-datascience-cookbook/notebooks/tutorials/floodmapping.html).

## Installation

To install the package, do the following:

```
pip install git+https://github.com/TUW-GEO/dask-flood-mapper
```


## Usage

Storm Babet hit the Denmark and Northern coast of Germany at the 20th of October 2023 [Wikipedia](https://en.wikipedia.org/wiki/Storm_Babet). Here an area around Zingst at the Baltic coast of Northern Germany is selected as the study area.

### Local Processing

Define the time range and geographic region in which the event occurred.

```python 
time_range = "2022-10-11/2022-10-25"
bbox = [12.3, 54.3, 13.1, 54.6]
```
Use the flood module and calculate the flood extent with the Bayesian decision method applied tp Sentinel-1 radar images. The object returned is a [`xarray`](https://docs.xarray.dev/en/stable/) with lazy loaded Dask arrays. To get the data in memory use the `compute` method on the returned object.

```python
from dask_flood_mapper import flood

flood.decision(bbox=bbox, datetime=time_range).compute()
```

### Distributed Processing

It is also possible to remotely process the data at the EODC [Dask Gateway](https://gateway.dask.org/) with the added benefit that we can then process close to the data source without requiring rate-limiting file transfers over the internet.

For ease of usage of the Dask Gateway install the [`eodc`]() package besides the `dask-gateway` package. Also, see the [EODC documentation](https://github.com/eodcgmbh/eodc-examples/blob/main/demos/dask.ipynb). 

```bash
pip install dask-gateway eodc
# or use pipenv sync -d
```

Connect to the gateway (this requires an EODC account).

```python
from eodc.dask import EODCDaskGateway
from rich.prompt import Prompt
your_username = Prompt.ask(prompt="Enter your Username")
gateway = EODCDaskGateway(username=your_username)
```

Create a cluster.

```
cluster = gateway.new_cluster(cluster_options)
client = cluster.get_client()
cluster.adapt(minimum=2, maximum=5)
```

Map the flood the same way as we have done when processing locally.

```python
flood.decision(bbox=bbox, datetime=time_range).compute()
```

### User Interface


It is also possible to run the workflow in an user-friendly interface instead of the Jupyter notebooks, as shown below:


![alt text](<docs/images/Screenshot from 2025-04-03 13-56-05.png>)


To access it, simyply run the in terminal the command:

```bash
floodmap
```

It will open the GUI in the web browser.


## Contributing Guidelines

Please find the contributing guielines in the specific file [here](CONTRIBUTING.md).

## Credits

Credits go to EODC ([https://eodc.eu](https://eodc.eu)) for developing the infrastructure and the management of the data required for this workflow. This work has been supported as part of the interTwin project ([https://www.intertwin.eu](https://www.intertwin.eu)). The interTwin project is funded by the European Union Horizon Europe Programme - Grant Agreement number 101058386.

Views and opinions expressed are however those of the authors only and do not necessarily reflect those of the European Union Horizon Europe/Horizon 2020 Programmes. Neither the European Union nor the granting authorities can be held responsible for them.

## Literature

1)  Bauer-Marschallinger, Bernhard, Senmao Cao, Mark Edwin Tupas, Florian Roth, Claudio Navacchi, Thomas Melzer, Vahid Freeman, and Wolfgang Wagner. â€œSatellite-Based Flood Mapping through Bayesian Inference from a Sentinel-1 SAR Datacube. Remote Sensing 14, no. 15 (January 2022): 3673. https://doi.org/10.3390/rs14153673.

## License

This repository is covered under the [MIT License](LICENSE.txt).
