import xarray as xr
import numpy as np

def calc_water_likelihood(dc):
    return  dc.MPLIA * -0.394181 + -4.142015

def harmonic_expected_backscatter(dc):
    w = np.pi * 2 / 365
    
    t = dc.time.dt.dayofyear
    wt = w * t
    
    M0 = dc.M0
    S1 = dc.S1
    S2 = dc.S2
    S3 = dc.S3
    C1 = dc.C1
    C2 = dc.C2
    C3 = dc.C3
    hm_c1 = (M0 + S1 * np.sin(wt)) + (C1 * np.cos(wt))
    hm_c2 = ((hm_c1 + S2 * np.sin(2 * wt)) + C2 * np.cos(2 * wt))
    hm_c3 = ((hm_c2 + S3 * np.sin(3 * wt)) + C3 * np.cos(3 * wt))
    return hm_c3

def bayesian_flood_decision(dc):
    
    nf_std = 2.754041
    sig0 = dc.sig0
    std = dc.STD
    wbsc = dc.wbsc
    hbsc = dc.hbsc

    f_prob = (1.0 / (std * np.sqrt(2 * np.pi))) * np.exp(-0.5 * \
        (((sig0 - wbsc) / nf_std) ** 2))
    nf_prob = (1.0 / (nf_std * np.sqrt(2 * np.pi))) * np.exp(-0.5 * \
        (((sig0 - hbsc) / nf_std) ** 2))
    
    evidence = (nf_prob * 0.5) + (f_prob * 0.5)
    nf_post_prob = (nf_prob * 0.5) / evidence
    f_post_prob = (f_prob * 0.5) / evidence
    decision = xr.where(np.isnan(f_post_prob) | np.isnan(nf_post_prob), np.nan, np.greater(f_post_prob, nf_post_prob))
    return nf_post_prob, f_post_prob, decision
