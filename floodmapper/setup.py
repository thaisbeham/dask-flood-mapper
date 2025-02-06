import yaml
import dask
from dask.distributed import Client, wait

# Load the YAML configuration once
def load_config(yaml_file):
    with open(yaml_file, 'r') as file:
        return yaml.safe_load(file)
# Load the config when the module is imported
config = load_config('config.yaml')


dask.config.set(temporary_directory='/tmp')
client = Client(**config["Daskclient"])



