from dask_flood_mapper.calculation import (
    calc_water_likelihood,
    harmonic_expected_backscatter,
    bayesian_flood_decision,
    bayesian_flood_probability,
    calculate_flood_dc,
    remove_speckles,
)
from dask_flood_mapper.setup import (
    initialize_catalog,
    initialize_search,
    search_parameters,
)
from dask_flood_mapper.processing import (
    post_processing,
    prepare_dc,
    process_sig0_dc,
    process_datacube,
    reproject_equi7grid,
    BANDS_HPAR
)
from dask_flood_mapper.setup import config

# import parameters from config.yaml file
crs = config["base"]["crs"]
chunks = config["base"]["chunks"]
groupby = config["base"]["groupby"]
BANDS_SIG0= "VV"
BANDS_PLIA = "MPLIA"


def decision(bbox, datetime):
    """
    Bayesian Flood Decision

    Classify Sentinel-1 radar images by simple Bayes inference into flood (1)
    and non-flood (0). Besides radar images, this algorithm relies on two other
    datasets stored at the Earth Observation Data Centre For Water Resources
    Monitoring (EODC); harmonic parameters based on a fit on per land pixel
    timeseries and the projected incidence angle of the measurement. The latter
    two datasets are required to calculate the land and water likelihood
    distributions, respectively.

    Parameters
    ----------
    bbox : tuple of float or tuple of int
        Geographic bounding box, consisting of minimum longitude, minimum
        latitude, maximum longitude, maximum latitude
    datetime: string
        Datetime string:

          - A closed range: "2022-10-01/2022-10-07"
          - Whole month, year or day: "2022-01"
          - Open range with current date: "2022-01-01/.."
          - Specific time instance: "2022-01-01T05:34:46"

    Returns
    -------
        flood decision : xarray.DataArray of 0 (non-flood) and 1 (flood)

    See also
    --------
    probability

    Examples
    --------
    >>> from dask_flood_mapper import flood
    >>>
    >>>
    >>> time_range = "2022-10-11/2022-10-25"
    >>> bbox = [12.3, 54.3, 13.1, 54.6]
    >>> flood.decision(bbox=bbox, datetime=time_range).compute()
    sigma naught datacube processed
    harmonic parameter datacube processed
    projected local incidence angle processed
    <xarray.DataArray 'decision' (time: 8, y: 1048, x: 2793)> Size: 187MB
    array([[[nan, nan, nan, ...,  0., nan, nan],
            [ 0.,  0.,  0., ...,  0., nan, nan],
            [ 0.,  0.,  0., ...,  0., nan, nan],
            ...,
            [nan, nan,  0., ...,  0.,  0.,  0.],
            [nan, nan,  0., ...,  0., nan, nan],
            [nan, nan,  0., ..., nan, nan, nan]],
        ...
           [[nan, nan, nan, ..., nan, nan, nan],
            [nan, nan, nan, ..., nan, nan, nan],
            [nan, nan, nan, ..., nan, nan, nan],
            ...,
            [nan, nan,  0., ...,  0.,  0.,  0.],
            [nan, nan,  0., ...,  0., nan, nan],
            [nan, nan,  0., ..., nan, nan, nan]],
        ...
           [[nan, nan, nan, ..., nan, nan, nan],
            [ 0.,  0.,  0., ..., nan, nan, nan],
            [ 0.,  0.,  0., ..., nan, nan, nan],
            ...,
            [nan, nan,  0., ...,  0.,  0.,  0.],
            [nan, nan,  0., ...,  0., nan, nan],
            [nan, nan,  0., ..., nan, nan, nan]],
        ...
           [[nan, nan, nan, ..., nan, nan, nan],
            [ 0.,  0.,  0., ..., nan, nan, nan],
            [ 0.,  0.,  0., ..., nan, nan, nan],
            ...,
            [nan, nan, nan, ..., nan, nan, nan],
            [nan, nan, nan, ..., nan, nan, nan],
            [nan, nan, nan, ..., nan, nan, nan]],
        ...
           [[nan, nan, nan, ...,  0., nan, nan],
            [ 0.,  0.,  0., ...,  0., nan, nan],
            [ 0.,  0.,  0., ...,  0., nan, nan],
            ...,
            [nan, nan,  0., ...,  0.,  0.,  0.],
            [nan, nan,  0., ...,  0., nan, nan],
            [nan, nan,  0., ..., nan, nan, nan]]])
    Coordinates:
    * x            (x) float64 22kB 12.3 12.3 12.3 12.3 ... 13.1 13.1 13.1 13.1
    * y            (y) float64 8kB 54.6 54.6 54.6 54.6 ... 54.3 54.3 54.3 54.3
    * time         (time) datetime64[ns] 64B 2022-10-11T05:25:01 ... 2022-10-23...
        spatial_ref  int64 8B 0
    Attributes:
        _FillValue:  nan
    >>>
    """

    sig0_dc, hpar_dc, plia_dc = preprocess(bbox, datetime)
    flood_dc = calculate_flood_dc(sig0_dc, plia_dc, hpar_dc)
    flood_dc["wbsc"] = calc_water_likelihood(flood_dc)  # Water
    flood_dc["hbsc"] = harmonic_expected_backscatter(flood_dc)  # Land
    flood_dc["decision"] = bayesian_flood_decision(flood_dc)
    flood_dc["f_post_prob"] = bayesian_flood_probability(flood_dc)
    flood_dc["nf_post_prob"] = 1 - flood_dc["f_post_prob"]
    flood_output = post_processing(flood_dc)
    return reproject_equi7grid(remove_speckles(flood_output), bbox=bbox)


def probability(bbox, datetime):
    sig0_dc, hpar_dc, plia_dc = preprocess(bbox, datetime)
    flood_dc = calculate_flood_dc(sig0_dc, plia_dc, hpar_dc)
    flood_dc["wbsc"] = calc_water_likelihood(flood_dc)  # Water
    flood_dc["hbsc"] = harmonic_expected_backscatter(flood_dc)  # Land
    return reproject_equi7grid(bayesian_flood_probability(flood_dc), bbox=bbox)


def preprocess(bbox, datetime):
    eodc_catalog = initialize_catalog()
    search = initialize_search(eodc_catalog, bbox, datetime)

    items_sig0 = search.item_collection()
    sig0_dc = prepare_dc(items_sig0, bbox, bands="VV")
    sig0_dc, orbit_sig0 = process_sig0_dc(sig0_dc, items_sig0, bands="VV")
    print("sigma naught datacube processed")

    search_hpar = search_parameters(eodc_catalog, bbox, collections="SENTINEL1_HPAR")
    items_hpar = search_hpar.item_collection()
    hpar_dc = prepare_dc(items_hpar, bbox, bands=BANDS_HPAR)
    hpar_dc = process_datacube(hpar_dc, items_hpar, orbit_sig0, BANDS_HPAR)
    print("harmonic parameter datacube processed")

    search_plia = search_parameters(eodc_catalog, bbox, collections="SENTINEL1_MPLIA")
    items_plia = search_plia.item_collection()
    plia_dc = prepare_dc(items_plia, bbox, bands=BANDS_PLIA)
    plia_dc = process_datacube(plia_dc, items_plia, orbit_sig0, bands="MPLIA")
    print("projected local incidence angle processed")

    return sig0_dc, hpar_dc, plia_dc
