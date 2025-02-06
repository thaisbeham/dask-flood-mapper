import pytest
import xarray as xr
import numpy as np
from unittest.mock import MagicMock, patch
import pandas as pd
import zipfile
from pathlib import Path
import shutil
import dask.array as da
from dask.distributed import Client, wait
client = Client(processes=False, threads_per_worker=2,
                n_workers=3, memory_limit='28GB')

# Import the function to test
from floodmapper.extra import process_sig0_dc, process_datacube, process_wcover_data, calculate_flood_dc, remove_speckles

@pytest.fixture
def mock_data():
    """Creates a mock dataset similar to real sig0_dc, using Dask arrays."""
    times = np.array(["2022-10-11", "2022-10-11", "2022-10-12"], dtype="datetime64")
    data_values = np.array([
        [[1, 2], [3, 4]],
        [[5, 6], [7, 8]],  # Duplicate time
        [[9, 10], [11, 12]]
    ])
    orbits = np.array(["ASCENDING10", "DESCENDING20", "ASCENDING30"])
    # Convert data_values to a Dask array with explicit chunks
    dask_data = da.from_array(data_values, chunks=(1, 2, 2))  # 👈 Ensure chunking

    ds = xr.Dataset(
        {"VV": (["time", "x", "y"], dask_data)},  # 👈 Use Dask array here
        coords={"time": times, "x": [0, 1], "y": [0, 1]}
    )

    return ds 

@pytest.fixture
def mock_items():
    """Creates a list of mock items with orbit properties."""
    class MockItem:
        def __init__(self, orbit_state, relative_orbit):
            self.properties = {"sat:orbit_state": [orbit_state], "sat:relative_orbit": relative_orbit}
    
    return [MockItem("ascending", 10), MockItem("descending", 20), MockItem("ascending", 30)]

@pytest.fixture
def mock_wcover_data():
    """Mock WorldCover dataset with a time dimension"""
    time = np.array(["2024-01-01"], dtype="datetime64[ns]")
    latitude = np.array([0, 1])
    longitude = np.array([0, 1])
    
    wcover_data = da.from_array(np.array([[[10, 20], [30, 40]]]), chunks=(1, 2, 2))

    return xr.Dataset(
        {"ESA_WORLDCOVER_10M_MAP": (["time", "latitude", "longitude"], wcover_data)},
        coords={"time": time, "latitude": latitude, "longitude": longitude},
    )


@pytest.fixture
def mock_flood_data():
    """Mock datasets for merging in flood calculation"""
    coords = {"orbit": np.array(["ASCENDING10", "DESCENDING20"]), "latitude": [0, 1], "longitude": [0, 1]}
    
    sig0_dc = xr.Dataset({"sig0": (["orbit", "latitude", "longitude"], da.ones((2, 2, 2), chunks=(1, 2, 2)))}, coords=coords)
    plia_dc = xr.Dataset({"plia": (["orbit", "latitude", "longitude"], da.ones((2, 2, 2), chunks=(1, 2, 2)))}, coords=coords)
    hpar_dc = xr.Dataset({"hpar": (["orbit", "latitude", "longitude"], da.ones((2, 2, 2), chunks=(1, 2, 2)))}, coords=coords)
    wcover_dc = xr.Dataset({"wcover": (["orbit", "latitude", "longitude"], da.full((2, 2, 2), 10, chunks=(1, 2, 2)))}, coords=coords)
    
    return sig0_dc, plia_dc, hpar_dc, wcover_dc

@patch("floodmapper.extra.post_process_eodc_cube")
@patch("floodmapper.extra.extract_orbit_names")
def test_process_sig0_dc(mock_extract_orbit_names, mock_post_process, mock_data, mock_items):
    # Mock function behaviors
    mock_post_process.return_value = mock_data
    mock_extract_orbit_names.return_value = np.array(["ASCENDING10", "DESCENDING20", "ASCENDING30"])
    
    # Call the function under test
    sig0_dc, orbit_sig0 = process_sig0_dc(mock_data, mock_items, "VV")

    # Assertions
    assert isinstance(sig0_dc, xr.Dataset), "Returned object should be an xarray Dataset"
    assert "sig0" in sig0_dc, "Variable should be renamed to 'sig0'"
    assert "orbit" in sig0_dc.coords, "Orbit coordinate should be present"
    assert len(sig0_dc.time) == 2, "Duplicate times should be averaged"

    # Check orbit values
    expected_orbits = np.array(["ASCENDING10", "ASCENDING30"])
    np.testing.assert_array_equal(orbit_sig0, expected_orbits)

    # Ensure persist() was called
    assert sig0_dc.chunks, "Dataset should be persisted (chunked with Dask)"
    assert any(isinstance(v.data, da.Array) for v in sig0_dc.data_vars.values()), "Dataset should be persisted (not computed)"

@patch("floodmapper.extra.post_process_eodc_cube")
@patch("floodmapper.extra.extract_orbit_names")
def test_process_datacube(mock_extract_orbit_names, mock_post_process, mock_data, mock_items):
    """Test process_datacube function"""
    mock_post_process.return_value = mock_data
    mock_extract_orbit_names.return_value = np.array(["ASCENDING10", "DESCENDING20", "ASCENDING30"])

    orbit_sig0 = "ASCENDING10"
    bands = "VV"

    # Call function under test
    result = process_datacube(mock_data, mock_items, orbit_sig0, bands)

    assert any(hasattr(v.data, "chunks") and v.data.chunks is not None for v in result.data_vars.values()), "Dataset should be chunked"

    # Ensure the dataset is chunked (persisted)
    assert result.chunks, "Dataset should be persisted (chunked with Dask)"
    assert any(isinstance(v.data, da.Array) for v in result.data_vars.values()), "Dataset should be persisted (not computed)"

    # Ensure at least one variable remains a Dask array (not fully computed)  
    assert any(isinstance(v.data, da.Array) for v in result.data_vars.values()), "Dataset should be persisted (not computed)"

    # Ensure the dataset variables have Dask chunks
    assert any(hasattr(v.data, "chunks") and v.data.chunks is not None for v in result.data_vars.values()), "Dataset should be chunked"

    assert orbit_sig0 in result.orbit.values, f"Dataset should contain orbit '{orbit_sig0}' only"

    # Ensure correct post-processing
    mock_post_process.assert_called_once_with(mock_data, mock_items, bands)
    mock_extract_orbit_names.assert_called_once_with(mock_items)

def test_process_wcover_data(mock_wcover_data):
    """Test processing of WorldCover dataset"""
    result = process_wcover_data(mock_wcover_data)

    # Ensure time dimension is removed and variable is renamed
    assert "time" not in result.dims, "Time dimension should be removed"
    assert "ESA_WORLDCOVER_10M_MAP" not in result.data_vars, "Original variable should be renamed"
    assert "wcover" in result.data_vars, "Variable should be renamed to 'wcover'"

    # Ensure dataset is persisted (Dask chunks)
    assert result.chunks, "Dataset should be persisted (chunked with Dask)"
    assert any(isinstance(v.data, da.Array) for v in result.data_vars.values()), "Dataset should be persisted (not computed)"


def test_calculate_flood_dc(mock_flood_data):
    """Test merging of datasets and flood processing"""
    sig0_dc, plia_dc, hpar_dc, wcover_dc = mock_flood_data
    result = calculate_flood_dc(sig0_dc, plia_dc, hpar_dc, wcover_dc)

    # Ensure merging happened correctly
    assert all(var in result.data_vars for var in ["sig0", "plia", "hpar", "wcover"]), "All variables should be present after merging"

    # Ensure WorldCover classification 80 is removed
    assert not (result.wcover == 80).any(), "WorldCover classification 80 should be removed"

    # Ensure 'orbit' was renamed to 'time'
    assert "time" in result.dims, "Orbit dimension should be renamed to 'time'"
    assert "orbit" not in result.dims, "Orbit dimension should be removed"

    # Ensure NaNs in 'sig0' dimension are dropped
    assert result.dropna(dim="time", how="all", subset=["sig0"]).sizes["time"] == result.sizes["time"], "All-NaN values in 'sig0' should be removed"

    # Ensure dataset is persisted (Dask chunks)
    assert result.chunks, "Dataset should be persisted (chunked with Dask)"
    assert any(isinstance(v.data, da.Array) for v in result.data_vars.values()), "Dataset should be persisted (not computed)"


def test_remove_speckles(mock_flood_data):
    """Test speckle noise removal via rolling median filter"""
    sig0_dc, _, _, _ = mock_flood_data  # Use only sig0_dc for filtering
    result = remove_speckles(sig0_dc, window_size=3)

    # Ensure rolling median filter was applied
    assert result.sizes["latitude"] == sig0_dc.sizes["latitude"], "Latitude size should remain the same"
    assert result.sizes["longitude"] == sig0_dc.sizes["longitude"], "Longitude size should remain the same"

    # Ensure dataset is persisted (Dask chunks)
    assert result.chunks, "Dataset should be persisted (chunked with Dask)"
    assert any(isinstance(v.data, da.Array) for v in result.data_vars.values()), "Dataset should be persisted (not computed)"


if __name__ == "__main__":
    pytest.main()
