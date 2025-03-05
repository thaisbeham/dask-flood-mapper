from dask_flood_mapper.processing import reproject_equi7grid
import numpy as np
import xarray as xr
import rioxarray  # noqa


def assert_datacube_eq(actual, expected):
    xr.testing.assert_allclose(actual, expected, rtol=0.01)


def make_full_datacube(shape, value):
    data = np.full(shape, value).astype(np.float32)
    input_cube = xr.DataArray(
        data,
        dims=("y", "x"),
        coords={"y": np.arange(shape[0]), "x": np.arange(shape[1])},
    ).rio.write_crs("EPSG:27704")
    return input_cube


def make_datacube(values, y, x):
    values_arr = np.array(values).astype(np.float32)
    return xr.DataArray(
        values_arr, dims=("y", "x"), coords={"y": y, "x": x}
    ).rio.write_crs("EPSG:27704")


def test_that_equi7_can_be_reprojected():
    input_cube = make_full_datacube((3, 3), 1)
    output_cube = reproject_equi7grid(input_cube, [-30, 16, -29, 17])
    assert_datacube_eq(
        output_cube,
        make_datacube(
            [
                [np.nan, np.nan, 1.0, np.nan],
                [np.nan, 1.0, 1.0, 1.0],
                [1.0, 1.0, 1.0, 1.0],
                [np.nan, 1.0, 1.0, np.nan],
            ],
            x=[-29.9, -29.9, -29.9, -29.9],
            y=[16.1, 16.1, 16.1, 16.1],
        ),
    )
