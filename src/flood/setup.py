import yaml
import dask
from dask.distributed import Client, wait
from pathlib import Path

dask.config.set(temporary_directory='/tmp')
client = Client(processes=False, threads_per_worker=2,
                n_workers=3, memory_limit='28GB' )

def load_config(yaml_file):
    with open(yaml_file, 'r') as file:
        return yaml.safe_load(file)



CONFIG_PATH = Path(__file__).resolve().parent / "config.yaml"
config = load_config(CONFIG_PATH)