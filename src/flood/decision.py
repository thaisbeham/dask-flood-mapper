from flood.calculation import calc_water_likelihood, harmonic_expected_backscatter, bayesian_flood_decision, calculate_flood_dc, remove_speckles
from flood.setup import initialize_catalog, initialize_search, search_parameters
from flood.processing import post_processing, prepare_dc, prepare_sig0dc, process_sig0_dc, process_datacube, process_wcover_data
from odc import stac as odc_stac
import os
import pystac_client
from flood.setup import config

# import parameters from config.yaml file
crs = config["base"]["crs"]
chunks = config["base"]["chunks"]
resolution =  config["base"]["resolution"]
groupby = config["base"]["groupby"]
bands_hpar= ("C1", "C2", "C3", "M0", "S1", "S2", "S3", "STD") # not possible to add to yaml file since is a ("a", "v") type
bands_plia = "MPLIA"


def flood_decision(bbox, datetime):
    eodc_catalog = initialize_catalog()
    search = initialize_search(eodc_catalog, bbox, datetime)

    # ---------- process the data

    # 20m datacube
    items_sig0 = search.item_collection()
    sig0_dc = prepare_sig0dc(items_sig0, bbox)
    sig0_dc, orbit_sig0 = process_sig0_dc(sig0_dc, items_sig0, bands= "VV") # Updated sig0_dc
    print("sig0_dc processed")
    #print(sig0_dc)

    # Harmonical parameters
    search_hpar = search_parameters(eodc_catalog, bbox, collections="SENTINEL1_HPAR")
    items_hpar =search_hpar.item_collection()
    hpar_dc = prepare_dc(items_hpar, bbox, bands=bands_hpar)
    hpar_dc = process_datacube(hpar_dc, items_hpar, orbit_sig0, bands_hpar)
    print("hpar_dc processed")
   # print(hpar_dc)


    # Local Incidence Angles
    search_plia= search_parameters(eodc_catalog, bbox, collections="SENTINEL1_MPLIA")
    items_plia = search_plia.item_collection()
    plia_dc = prepare_dc(items_plia, bbox, bands=bands_plia)
    plia_dc = process_datacube(plia_dc, items_plia, orbit_sig0, bands="MPLIA")
    print("plia_dc processed")
    #print(plia_dc)

    # ESA World Cover data
    os.environ['AWS_NO_SIGN_REQUEST'] = 'YES'
    wcover_catalog = pystac_client.Client.open('https://services.terrascope.be/stac/')
    search_wcover = search_parameters(wcover_catalog, bbox, collections="urn:eop:VITO:ESA_WorldCover_10m_2021_AWS_V2") #maybe put also collections inside yaml file
    items_wcover = search_wcover.item_collection()
    wcover_dc = odc_stac.load(items_wcover, crs=crs, chunks=chunks, resolution=resolution, bbox=bbox)
    wcover_dc = process_wcover_data(wcover_dc)
    print("wcover_dc processed")
    #print(wcover_dc)

    # ------------ calculations

    # fuse cube
    flood_dc = calculate_flood_dc(sig0_dc, plia_dc, hpar_dc, wcover_dc)

    # Likelihoods
    flood_dc["wbsc"] = calc_water_likelihood(flood_dc) # Water
    flood_dc["hbsc"] = harmonic_expected_backscatter(flood_dc) # Land

    # Decision
    flood_dc[["nf_post_prob", "f_post_prob", "decision"]] = bayesian_flood_decision(flood_dc)
    decision = flood_dc[["decision"]]


    # -------------- post processing
    
    flood_output = post_processing(flood_dc)
    flood_output = remove_speckles(flood_output)

    return flood_output












