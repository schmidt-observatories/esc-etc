from stp_etc_esc import ExposureTimeSNRCalculatorESC as etsc  # import the package
from astropy import units as u
from pathlib import Path
import numpy as np
import matplotlib.pyplot as plt
import matplotlib as mpl
import logging
import time

def esc_calc_snr(exp_time,
                 int_time,
                 hoststarmag=-0.353,
                 contrast=1e-8,
                 planetdeltamag=20,
                 bg_flux=22.5,
                 exobg_flux=21,
                 flux_units='vega',
                 verbose=True,
                 plot=False):
    """
    INPUT:
        exp_time: Total exposure time in seconds
        int_time: Integration time in seconds
        hoststarmag: host star magnitude
        contrast

    QUESTIONS:
        How to change the config params?

        https://github.com/uasal/config_um_esc
    """
    ESC = etsc.Observatory(telescope_name="Extrasolar Camera",
                           telescope_diameter=6.5*u.m, # change to 3?
                           telescope_focal_len=97.5*u.m) # Focal length 15 * 3 = 45m
    t0 = time.perf_counter()
    #ESC.get_info()

    pre_t = time.perf_counter()
    preconfig_ESC = ESC.make_STP(subap='A',
                                 plot=plot,
                                 telconfig='DEFAULT',
                                 escconfig='DEFAULT',
                                 telpath='DEFAULT',
                                 escpath='DEFAULT',
                                 contrast='spec')
    if verbose:
        print('######################################################')
        print('######################################################')
        print(f"make_STP() took: {time.perf_counter() - pre_t:.3f} s")
        print('######################################################')
        print('######################################################')
 
    if verbose:
        print('#################################')
        print('#################################')
        print('Setting contrast to: ',contrast)
    ESC.set_generic_source(contrast,0,plot=plot)

    #zodi_model = stp_support_path / Path(stp_config['astrophysics']['zodi']['profile'])

    if verbose:
        print('#################################')
        print('#################################')
        print('Setting background to: ',ESC.background_name)
    bg_t = time.perf_counter()
    ESC.set_background(background_file = None, plot=plot) #None background file gives default background file from internal config
    if verbose:
        print('######################################################')
        print('######################################################')
        print(f"set_background() took: {time.perf_counter() - bg_t:.3f} s")
        print('######################################################')
        print('######################################################')

    if verbose:
        print(ESC.background_name, '\n'*2, ESC.background_spectrum, '\n'*2)

    if verbose:
        print('#################################')
        print('#################################')
        print('Making observation')
    obs_t = time.perf_counter()
    ESC.make_observation(hoststarflux=hoststarmag,
                         planetdeltamag=planetdeltamag,
                         bg_flux=bg_flux,
                         flux_units=flux_units,
                         plot=plot,
                         exobg_flux=exobg_flux)
    if verbose:
        print('######################################################')
        print('######################################################')
        print(f"make_observation() took: {time.perf_counter() - obs_t:.3f} s")
        print('######################################################')
        print('######################################################')

    #ESC.calc_saturation_time()
    if verbose:
        print('#################################')
        print('#################################')
        print('Calculating SNR')
    snr_t = time.perf_counter()
    snr = ESC.calc_SNR(exp_time*u.s,
                       int_time*u.s)
    if verbose:
        print('######################################################')
        print('######################################################')
        print(f"calc_SNR() took: {time.perf_counter() - snr_t:.3f} s")
        print('######################################################')
        print('######################################################')
    if verbose:
        print('######################################################')
        print('######################################################')
        print(f"Total esc_calc_snr() time: {time.perf_counter() - t0:.3f} s")
        print('######################################################')
        print('######################################################')
    return snr

if __name__=='__main__':
    exp_time = 600
    int_time = 10

    # Calculate SNR time
    snr = esc_calc_snr(exp_time,int_time,verbose=True)
    print(f"SNR: {snr}")