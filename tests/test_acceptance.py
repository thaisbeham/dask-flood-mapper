# import xarray as xr
# from dask_flood_mapper import flood
# import numpy as np
# import pytest


# class TestFloodMapNorthernGermany2022:
#     time_range = "2022-10-11/2022-10-25"
#     minlon, maxlon = 12.999, 13
#     minlat, maxlat = 53.999, 54
#     bounding_box = [minlon, minlat, maxlon, maxlat]
#     flood_map = flood.decision(bbox=bounding_box, datetime=time_range)

#     def test_that_flood_map_is_created(self):
#         xr.testing.assert_equal(self.flood_map, xr.DataArray([0, 1]))

#     def test_that_flood_map_is_xarray(self):
#         assert isinstance(self.flood_map, xr.DataArray)

#     def test_that_flood_map_values_are_binary(self):
#         np.testing.assert_equal(np.unique(self.flood_map.values), np.array([0, 1]))


# class TestFloodMapIsOutOfDateRange:
#     minlon, maxlon = 12.3, 13.1
#     minlat, maxlat = 54.3, 54.6
#     bounding_box = [minlon, minlat, maxlon, maxlat]

#     def test_that_datetime_is_too_specific(self):
#         with pytest.raises(ValueError):
#             flood.decision(bbox=self.bounding_box, datetime="2022-10-11:20:22")

#     def test_that_datetime_is_out_of_range(self):
#         with pytest.raises(ValueError):
#             flood.decision(bbox=self.bounding_box, datetime="2011-10-11/2011-10-25")
