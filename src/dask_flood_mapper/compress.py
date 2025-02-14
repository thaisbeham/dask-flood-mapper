import zipfile
from pathlib import Path
import shutil

def _zip(file):
    filename = Path(file).with_suffix(".zarr.zip")
    with zipfile.ZipFile(
        filename, "w", compression=zipfile.ZIP_STORED, allowZip64=True) as fh:
        fh.write(filename, filename)
    shutil.rmtree(file)

def write_zarr_and_zip(ds, filename):
    """ Write a dataset to zarr and zip the zarr file"""
    ds.to_zarr(filename, mode='w')
    _zip(filename)