import pytest
import xarray as xr
import numpy as np
from unittest.mock import MagicMock
import pandas as pd
import zipfile
from pathlib import Path
import shutil

from floodmapper.processing import extract_orbit_names, post_process_eodc_cube, post_process_eodc_cube_, post_processing
from floodmapper.calculation import calc_water_likelihood, harmonic_expected_backscatter, bayesian_flood_decision
from floodmapper.compress import _zip, write_zarr_and_zip

@pytest.fixture
def mock_item():
    item = MagicMock()
    item.assets = {
        "band1": MagicMock(extra_fields={'raster:bands': [{'scale': 2, 'nodata': -9999}]})
    }
    return [item]  # Return as list

@pytest.fixture
def dataset():
    return xr.Dataset({"band1": (["x", "y"], [[1, 2], [3, 4]])})

@pytest.fixture
def data_array():
    return xr.DataArray([[1, 2], [3, 4]], dims=("x", "y"))

class MockItem:
    """Mock class for satellite items."""
    def __init__(self, orbit_state, relative_orbit):
        self.properties = {
            "sat:orbit_state": [orbit_state],
            "sat:relative_orbit": relative_orbit
        }

@pytest.fixture
def mock_items():
    return [
        MockItem("ascending", 10),
        MockItem("descending", 20),
        MockItem("ascending", 30)
    ]

@pytest.fixture
def mock_dataset():
    # Create a mock dataset with 'time', and the necessary variables for harmonic backscatter computation
    time = pd.date_range("2022-01-01", periods=365, freq="D")  # Create a time range for 1 year
    M0 = np.random.random(365)
    S1 = np.random.random(365)
    S2 = np.random.random(365)
    S3 = np.random.random(365)
    C1 = np.random.random(365)
    C2 = np.random.random(365)
    C3 = np.random.random(365)
    
    return xr.Dataset({
        "M0": ("time", M0),
        "S1": ("time", S1),
        "S2": ("time", S2),
        "S3": ("time", S3),
        "C1": ("time", C1),
        "C2": ("time", C2),
        "C3": ("time", C3),
    }, coords={"time": time})

@pytest.fixture
def sample_dataset():
    """Creates a simple Xarray dataset for testing Zarr writing."""
    return xr.Dataset({
        "temperature": (["x", "y"], [[15, 20], [22, 30]]),
        "humidity": (["x", "y"], [[0.8, 0.7], [0.6, 0.9]])
    })

@pytest.fixture
def temp_zarr_filename(tmp_path):
    """Provides a temporary filename for Zarr file storage."""
    return tmp_path / "test_dataset.zarr"

class TestPostProcessEODC:

    # Test extract_orbit_names
    def test_extract_orbit_names(self, mock_items):
        result = extract_orbit_names(mock_items)
        expected = np.array(["ASCENDING10", "DESCENDING20", "ASCENDING30"])
        assert np.array_equal(result, expected)

    def test_empty_items(self):
        result = extract_orbit_names([])
        expected = np.array([])
        assert np.array_equal(result, expected)

    def test_incomplete_properties(self):
        incomplete_items = [
            MockItem("ascending", 10),
            MockItem("", 20)  # Empty orbit state
        ]
        result = extract_orbit_names(incomplete_items)
        expected = np.array(["ASCENDING10", "20"])  
        assert np.array_equal(result, expected)

    # Test post_process_eodc_cube_
    def test_post_process_eodc_cube_(self, dataset, mock_item):
        expected = dataset /2
        result = post_process_eodc_cube_(dataset, mock_item, "band1")
        print(f"Dataset:  {dataset.band1}")
        assert result.equals(expected)

    # Test post_process_eodc_cube
    def test_post_process_eodc_cube(self, dataset, mock_item):
        expected = dataset.band1 /2
        result = post_process_eodc_cube(dataset, mock_item, "band1")

        assert result.band1.equals(expected)

    # Test calc_water_likelihood
    def test_calc_water_likelihood(self, dataset):
        # Create mock MPLIA data
        mplia_values = np.array([[10, 20], [30, 40]])
        dataset["MPLIA"] = (["x", "y"], mplia_values)
        
        # Expected result calculation
        expected_values = mplia_values * -0.394181 + -4.142015
        
        result = calc_water_likelihood(dataset)

        # Assert that the result equals the expected values
        np.testing.assert_allclose(result.values, expected_values, rtol=1e-5)

            # Test harmonic_expected_backscatter
    def test_harmonic_expected_backscatter(self, mock_dataset):
        # Call the function
        result = harmonic_expected_backscatter(mock_dataset)

        # Compute the expected values based on the formula manually
        w = np.pi * 2 / 365
        t = mock_dataset.time.dt.dayofyear
        wt = w * t
        
        M0 = mock_dataset.M0
        S1 = mock_dataset.S1
        S2 = mock_dataset.S2
        S3 = mock_dataset.S3
        C1 = mock_dataset.C1
        C2 = mock_dataset.C2
        C3 = mock_dataset.C3
        
        # Compute expected result
        hm_c1 = (M0 + S1 * np.sin(wt)) + (C1 * np.cos(wt))
        hm_c2 = ((hm_c1 + S2 * np.sin(2 * wt)) + C2 * np.cos(2 * wt))
        expected = ((hm_c2 + S3 * np.sin(3 * wt)) + C3 * np.cos(3 * wt))

        # Use assert to compare results
        assert (result.values == expected.values).all()

    def test_bayesian_flood_decision(self, mock_dataset):
        # Create mock data
        mock_dataset["sig0"] = (["x", "y"], [[1, 2], [3, 4]])
        mock_dataset["STD"] = (["x", "y"], [[0.5, 0.5], [0.5, 0.5]])
        mock_dataset["wbsc"] = (["x", "y"], [[0.1, 0.2], [0.3, 0.4]])
        mock_dataset["hbsc"] = (["x", "y"], [[0.5, 0.6], [0.7, 0.8]])

        # Call the function
        nf_post_prob, f_post_prob, decision = bayesian_flood_decision(mock_dataset)

        # Manually calculate expected values using the formula
        nf_std = 2.754041
        sig0 = mock_dataset.sig0
        std = mock_dataset.STD
        wbsc = mock_dataset.wbsc
        hbsc = mock_dataset.hbsc

        f_prob = (1.0 / (std * np.sqrt(2 * np.pi))) * np.exp(-0.5 * \
            (((sig0 - wbsc) / nf_std) ** 2))
        nf_prob = (1.0 / (nf_std * np.sqrt(2 * np.pi))) * np.exp(-0.5 * \
            (((sig0 - hbsc) / nf_std) ** 2))

        evidence = (nf_prob * 0.5) + (f_prob * 0.5)
        nf_post_prob_expected = (nf_prob * 0.5) / evidence
        f_post_prob_expected = (f_prob * 0.5) / evidence
        decision_expected = np.greater(f_post_prob_expected, nf_post_prob_expected)

        # Use assert to compare results
        assert (nf_post_prob.values == nf_post_prob_expected.values).all()
        assert (f_post_prob.values == f_post_prob_expected.values).all()
        assert (decision.values == decision_expected).all()

    # Test post_processing
    def test_post_processing(self, mock_dataset):
        # Create mock data
        mock_dataset["sig0"] = (["x", "y"], [[10, 15], [30, 35]])
        mock_dataset["hbsc"] = (["x", "y"], [[0.3, 0.6], [0.7, 0.8]])
        mock_dataset["wbsc"] = (["x", "y"], [[0.1, 0.4], [0.5, 0.9]])
        mock_dataset["MPLIA"] = (["x", "y"], [[40, 35], [25, 45]])
        mock_dataset["STD"] = (["x", "y"], [[1.5, 1.7], [1.6, 1.9]])
        mock_dataset["f_post_prob"] = (["x", "y"], [[0.9, 0.85], [0.75, 0.95]])
        mock_dataset["decision"] = (["x", "y"], [[True, False], [True, True]])

        # Call the function
        decision = post_processing(mock_dataset)

        # Expected decision computation
        expected_decision = np.logical_and(mock_dataset.MPLIA >= 27, mock_dataset.MPLIA <= 48) \
                            * (mock_dataset.hbsc > (mock_dataset.wbsc + 0.5 * 2.754041)) \
                            * ((mock_dataset.sig0 > (mock_dataset.hbsc - 3 * mock_dataset.STD)) & 
                               (mock_dataset.sig0 < (mock_dataset.hbsc + 3 * mock_dataset.STD))) \
                            * (mock_dataset.sig0 < (mock_dataset.wbsc + 3 * 2.754041)) \
                            * (mock_dataset.f_post_prob > 0.8)

        # Compare result and expected values
        print(f"Resulting decision: {decision.values}")
        print(f"Expected decision: {expected_decision.values}")
        
        # Use assert to compare results
        #assert (decision.values == expected_decision.values).all()
        assert np.array_equal(decision.values, expected_decision)




class TestZarrFunctions:
    def test_zip_function(self, sample_dataset, temp_zarr_filename):
        """Test _zip() to ensure it creates a zipped Zarr file and deletes the original."""
        sample_dataset.to_zarr(temp_zarr_filename, mode='w')
        _zip(temp_zarr_filename)

        zipped_filename = Path(str(temp_zarr_filename) + ".zip")

        assert zipped_filename.exists(), "Zipped file was not created."
        assert not temp_zarr_filename.exists(), "Original Zarr directory was not deleted."

    def test_write_zarr_and_zip(self, sample_dataset, temp_zarr_filename):
        """Test write_zarr_and_zip() end-to-end to verify writing and zipping."""
        write_zarr_and_zip(sample_dataset, temp_zarr_filename)

        zipped_filename = Path(str(temp_zarr_filename) + ".zip")

        assert zipped_filename.exists(), "Zipped file was not created."
        assert not temp_zarr_filename.exists(), "Original Zarr directory was not deleted."

        with zipfile.ZipFile(zipped_filename, 'r') as z:
            assert len(z.namelist()) > 0, "Zipped archive is empty."



if __name__ == "__main__":
    pytest.main()
