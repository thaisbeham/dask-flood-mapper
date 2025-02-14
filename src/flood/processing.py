import xarray as xr
import numpy as np
from odc import stac as odc_stac
from flood.setup import config
import numpy as np
import xarray as xr
from dask.distributed import wait


# import parameters from config.yaml file
crs = config["base"]["crs"]
chunks = config["base"]["chunks"]
resolution =  config["base"]["resolution"]
groupby = config["base"]["groupby"]
bands_hpar= ("C1", "C2", "C3", "M0", "S1", "S2", "S3", "STD") # not possible to add to yaml file since is a ("a", "v") type
bands_plia = "MPLIA" 

# pre-processing
def prepare_sig0dc(items_sig0,bbox):

    sig0_dc = odc_stac.load(items_sig0,
                        bands= "VV",
                        crs=crs,
                        chunks=chunks,
                        resolution=resolution,
                        bbox=bbox,
                        resampling="bilinear",
                        groupby=groupby,
                        )
    return sig0_dc

def prepare_dc(items_hpar, bbox, bands):
    hpar_dc = odc_stac.load(items_hpar,
                        bands=bands,
                        crs=crs,
                        chunks=chunks,
                        resolution=resolution,
                        bbox=bbox,
                        groupby=groupby,
                        )
    
    return hpar_dc

# processing
def process_sig0_dc(sig0_dc, items_sig0, bands):
    
    sig0_dc = (post_process_eodc_cube(sig0_dc, items_sig0, bands)
               .rename_vars({"VV": "sig0"})
               .assign_coords(orbit=("time", extract_orbit_names(items_sig0)))
               .dropna(dim="time", how="all")
               .sortby("time"))
    
    __, indices = np.unique(sig0_dc.time, return_index=True)
    indices.sort()

    orbit_sig0 = sig0_dc.orbit[indices].data

    sig0_dc = sig0_dc.groupby("time").mean(skipna=True)
    
    sig0_dc = sig0_dc.assign_coords(orbit=("time", orbit_sig0))

    sig0_dc = sig0_dc.persist()
    wait(sig0_dc)  

    return sig0_dc, orbit_sig0

def process_datacube(datacube, items_dc,orbit_sig0, bands ):
    
    datacube = post_process_eodc_cube(datacube, items_dc, bands).rename({"time": "orbit"})
    
    datacube["orbit"] = extract_orbit_names(items_dc)
    
    datacube = datacube.groupby("orbit").mean(skipna=True)

    datacube = datacube.sel(orbit=orbit_sig0)

    datacube = datacube.persist()
    wait(datacube)  
    return datacube

# post-processing
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
