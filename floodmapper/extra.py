#import required packages

import numpy as np
import xarray as xr
from dask.distributed import wait
from floodmapper.processing import post_process_eodc_cube, extract_orbit_names



def process_sig0_dc(sig0_dc, items_sig0, bands):
    # Step 1: Post-process EODC cube
    sig0_dc = (post_process_eodc_cube(sig0_dc, items_sig0, bands)
               .rename_vars({"VV": "sig0"})
               .assign_coords(orbit=("time", extract_orbit_names(items_sig0)))
               .dropna(dim="time", how="all")
               .sortby("time"))
    
    # Step 2: Get unique time indices and sort
    __, indices = np.unique(sig0_dc.time, return_index=True)
    indices.sort()

    # Step 3: Extract orbit names
    orbit_sig0 = sig0_dc.orbit[indices].data

    # Step 4: Remove duplicate time dimension by grouping and averaging
    sig0_dc = sig0_dc.groupby("time").mean(skipna=True)
    
    # Step 5: Assign the orbit names to the time dimension
    sig0_dc = sig0_dc.assign_coords(orbit=("time", orbit_sig0))

    # Step 6: Persist the data and wait
    sig0_dc = sig0_dc.persist()
    wait(sig0_dc)  # Assuming wait is a valid function

    return sig0_dc, orbit_sig0
    

def process_datacube(datacube, items_dc,orbit_sig0, bands ):
    # Step 1: Post-process EODC cube and rename 'time' to 'orbit'
    datacube = post_process_eodc_cube(datacube, items_dc, bands).rename({"time": "orbit"})
    
    # Step 2: Extract orbit names and assign to 'orbit' dimension
    datacube["orbit"] = extract_orbit_names(items_dc)
    
    # Step 3: Group by 'orbit' and calculate the mean
    datacube = datacube.groupby("orbit").mean(skipna=True)

 
    datacube = datacube.sel(orbit=orbit_sig0)

    # Step 5: Persist the data and wait
    datacube = datacube.persist()
    wait(datacube)  # Assuming wait is a valid function

    return datacube

def process_wcover_data(wcover_dc):
    """Process a preloaded WorldCover dataset by removing the time dimension and renaming variables."""
    
    wcover_dc = (wcover_dc
                 .squeeze("time")
                 .drop_vars("time")
                 .rename_vars({"ESA_WORLDCOVER_10M_MAP": "wcover"}))
    
    # Persist the data and wait
    wcover_dc = wcover_dc.persist()
    wait(wcover_dc)  # Assuming wait() is a valid function

    return wcover_dc

def calculate_flood_dc(sig0_dc, plia_dc, hpar_dc, wcover_dc):
    """Merge four data cubes and apply processing steps to clean and filter the dataset."""
    
    # Merge the data cubes
    flood_dc = xr.merge([sig0_dc, plia_dc, hpar_dc, wcover_dc])

    # Remove areas where WorldCover classification is 80
    flood_dc = flood_dc.where(flood_dc.wcover != 80)

    # Process the data: reset index, rename orbit to time, and drop NaNs in 'sig0'
    flood_dc = (flood_dc
                .reset_index("orbit", drop=True)
                .rename({"orbit": "time"})
                .dropna(dim="time", how="all", subset=["sig0"]))

    # Persist and wait for processing
    flood_dc = flood_dc.persist()
    wait(flood_dc)  # Assuming wait() is a valid function

    return flood_dc

def remove_speckles(flood_output, window_size=5):
    """Apply a rolling median filter to smooth the dataset spatially over longitude and latitude."""
    
    flood_output = (flood_output
                    .rolling({"longitude": window_size, "latitude": window_size}, center=True)
                    .median(skipna=True)
                    .persist())

    wait(flood_output)  # Assuming wait() is a valid function
    
    return flood_output