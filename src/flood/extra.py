#import required packages

import numpy as np
import xarray as xr
from dask.distributed import wait
from flood.processing import post_process_eodc_cube, extract_orbit_names



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

def process_wcover_data(wcover_dc):
    """Process a preloaded WorldCover dataset by removing the time dimension and renaming variables."""
    
    wcover_dc = (wcover_dc
                 .squeeze("time")
                 .drop_vars("time")
                 .rename_vars({"ESA_WORLDCOVER_10M_MAP": "wcover"}))
    

    wcover_dc = wcover_dc.persist()
    wait(wcover_dc)  

    return wcover_dc

def calculate_flood_dc(sig0_dc, plia_dc, hpar_dc, wcover_dc):
    """Merge four data cubes and apply processing steps to clean and filter the dataset."""
    
    flood_dc = xr.merge([sig0_dc, plia_dc, hpar_dc, wcover_dc])

    flood_dc = flood_dc.where(flood_dc.wcover != 80)

    flood_dc = (flood_dc
                .reset_index("orbit", drop=True)
                .rename({"orbit": "time"})
                .dropna(dim="time", how="all", subset=["sig0"]))

    flood_dc = flood_dc.persist()
    wait(flood_dc) 

    return flood_dc

def remove_speckles(flood_output, window_size=5):
    """Apply a rolling median filter to smooth the dataset spatially over longitude and latitude."""
    
    flood_output = (flood_output
                    .rolling({"longitude": window_size, "latitude": window_size}, center=True)
                    .median(skipna=True)
                    .persist())

    wait(flood_output) 
    
    return flood_output