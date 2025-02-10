import xarray as xr
import numpy as np



def post_process_eodc_cube(dc: xr.Dataset, items, bands):
    if not isinstance(bands, tuple):
        bands = tuple([bands])
    for i in bands:
        dc[i] = post_process_eodc_cube_(dc[i], items, i)
    return dc

def post_process_eodc_cube_(dc: xr.DataArray, items, band):
    scale = items[0].assets[band].extra_fields.get('raster:bands')[0]['scale']
    nodata = items[0].assets[band].extra_fields.get('raster:bands')[0]['nodata']
    # Apply the scaling and nodata masking logic
    return dc.where(dc != nodata) / scale


def extract_orbit_names(items):
    return np.array([items[i].properties["sat:orbit_state"][0].upper() + \
                     str(items[i].properties["sat:relative_orbit"]) \
                     for i in range(len(items))])

def post_processing(dc):
    dc = dc * np.logical_and(dc.MPLIA >= 27, dc.MPLIA <= 48)
    dc = dc * (dc.hbsc > (dc.wbsc + 0.5 * 2.754041))
    land_bsc_lower = dc.hbsc - 3 * dc.STD
    land_bsc_upper = dc.hbsc + 3 * dc.STD
    water_bsc_upper = dc.wbsc + 3 * 2.754041
    mask_land_outliers = np.logical_and(dc.sig0 > land_bsc_lower, dc.sig0 < land_bsc_upper)
    mask_water_outliers = dc.sig0 < water_bsc_upper
    dc = dc * (mask_land_outliers | mask_water_outliers)
    return  (dc * (dc.f_post_prob > 0.8)).decision
