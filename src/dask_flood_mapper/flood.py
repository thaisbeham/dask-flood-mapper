from dask_flood_mapper.calculation import calc_water_likelihood, harmonic_expected_backscatter, bayesian_flood_decision, calculate_flood_dc, remove_speckles
from dask_flood_mapper.setup import initialize_catalog, initialize_search, search_parameters
from dask_flood_mapper.processing import post_processing, prepare_dc, prepare_sig0dc, process_sig0_dc, process_datacube
from odc import stac as odc_stac
import os
import pystac_client
from dask_flood_mapper.setup import config

# import parameters from config.yaml file
crs = config["base"]["crs"]
chunks = config["base"]["chunks"]
resolution =  config["base"]["resolution"]
groupby = config["base"]["groupby"]
bands_hpar= ("C1", "C2", "C3", "M0", "S1", "S2", "S3", "STD") # not possible to add to yaml file since is a ("a", "v") type
bands_plia = "MPLIA"


def decision(bbox, datetime):
    eodc_catalog = initialize_catalog()
    search = initialize_search(eodc_catalog, bbox, datetime)

    # ---------- process the data

    # 20m datacube
    items_sig0 = search.item_collection()
    sig0_dc = prepare_sig0dc(items_sig0, bbox)
    sig0_dc, orbit_sig0 = process_sig0_dc(sig0_dc, items_sig0, bands= "VV") # Updated sig0_dc
    print("sig0_dc processed")

    # Harmonical parameters
    search_hpar = search_parameters(eodc_catalog, bbox, collections="SENTINEL1_HPAR")
    items_hpar =search_hpar.item_collection()
    hpar_dc = prepare_dc(items_hpar, bbox, bands=bands_hpar)
    hpar_dc = process_datacube(hpar_dc, items_hpar, orbit_sig0, bands_hpar)
    print("hpar_dc processed")
   

    # Local Incidence Angles
    search_plia= search_parameters(eodc_catalog, bbox, collections="SENTINEL1_MPLIA")
    items_plia = search_plia.item_collection()
    plia_dc = prepare_dc(items_plia, bbox, bands=bands_plia)
    plia_dc = process_datacube(plia_dc, items_plia, orbit_sig0, bands="MPLIA")
    print("plia_dc processed")
    

    # ------------ calculations

    # fuse cube
    flood_dc = calculate_flood_dc(sig0_dc, plia_dc, hpar_dc)

    # Likelihoods
    flood_dc["wbsc"] = calc_water_likelihood(flood_dc) # Water
    flood_dc["hbsc"] = harmonic_expected_backscatter(flood_dc) # Land

    # Decision
    flood_dc[["nf_post_prob", "f_post_prob", "decision"]] = bayesian_flood_decision(flood_dc)


    # -------------- post processing
    
    flood_output = post_processing(flood_dc)
    flood_output = remove_speckles(flood_output)

    return flood_output
  