import yaml
import dask
from dask.distributed import Client
import pystac_client
from importlib.resources import files
from appdirs import user_config_dir
from pathlib import Path
import shutil

dask.config.set(temporary_directory="/tmp")
client = Client(processes=False, threads_per_worker=2, n_workers=3, memory_limit="28GB")


def load_config(yaml_file):
    with open(yaml_file, "r") as file:
        return yaml.safe_load(file)


CONFIG_PATH = files("dask_flood_mapper").joinpath("config.yaml")
USER_CONFIG_PATH = Path(user_config_dir("dask_flood_mapper")) / "config.yaml"

config = load_config(CONFIG_PATH)


def get_user_config():
    if USER_CONFIG_PATH.exists():
        return USER_CONFIG_PATH
    else:
        print("User configuration does not exist.")


def set_user_config():
    get_user_config()
    return shutil.copy(CONFIG_PATH, USER_CONFIG_PATH / "config.yaml")


def initialize_catalog():
    eodc_catalog = pystac_client.Client.open(config["api"])
    return eodc_catalog


def initialize_search(eodc_catalog, bbox, time_range):
    search = eodc_catalog.search(
        collections="SENTINEL1_SIG0_20M",
        bbox=bbox,
        datetime=time_range,
    )
    return search


def search_parameters(eodc_catalog, bbox, collections):
    search = eodc_catalog.search(
        collections=collections,  # "SENTINEL1_HPAR" or "SENTINEL1_MPLIA"
        bbox=bbox,
    )

    return search
