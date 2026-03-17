import matplotlib
matplotlib.use("Agg")

import pytest
import numpy as np
import os
import importlib.util
import astropy.units as u
from synphot import SpectralElement
from synphot.models import Box1D
import astropy.units as u

try:
    import config_stp
    import config_stp_esc
    import config_um
except:
    print("Could not import configuration repos.")

try:
    import utils_config
except:
    print("Could not import utils_config. Cannot parse tomls. Exiting.")
    exit()

from stp_etc_esc import ExposureTimeSNRCalculatorESC as etsc

#@pytest.fixture
#def UM():
#	return "UM"

@pytest.fixture
def STP():
	return "STP"

@pytest.fixture
def telescope(request):
    return request.getfixturevalue(request.param)

@pytest.fixture
def test_STP():
	return "test_STP"


@pytest.mark.parametrize("telescope", ["STP"], indirect=True)
def test_configs_telescope(telescope):
	if telescope == "STP":
		data_telescope = config_stp.load_config_values("parsed")
	if telescope == "test_STP":
		test_loader = utils_config.ConfigLoader('test_data/test_STP')
		data_telescope = test_loader.load_configs()
	#if telescope == "UM":
	#	data_telescope = config_um.load_config_values("parsed")

	assert "value" in data_telescope['observatory']['pointing']['jitter_rms'], f"data_telescope['observatory']['pointing']['jitter_rms'] could not be verified in {telescope} config"
	assert "value" in data_telescope['telescope']['optics']['m1']['aper_clear_OD'], f"data_telescope['telescope']['optics']['m1']['aper_clear_OD'] could not be verified in {telescope} config"
	assert "value" in data_telescope['telescope']['optics']['m1']['surface_rms'], f"data_telescope['telescope']['optics']['m1']['surface_rms'] could not be verified in {telescope} config"
	assert isinstance(data_telescope['telescope']['general']['f_number'], float), f"data_telescope['telescope']['general']['f_number'] could not be verified in {telescope} config"
	assert "value" in data_telescope['telescope']['optics']['m2']['aper_clear_OD'], f"data_telescope['telescope']['optics']['m2']['aper_clear_OD'] could not be verified in {telescope} config"
	assert "value" in data_telescope['telescope']['optics']['m2']['support_width'], f"data_telescope['telescope']['optics']['m2']['support_width'] could not be verified in {telescope} config"
	assert isinstance(data_telescope['telescope']['optics']['m2']['n_supports'], int), f"data_telescope['telescope']['optics']['m2']['n_supports'] could not be verified in {telescope} config"

	return

def test_configs_instrument():
	data_instrument = config_stp_esc.load_config_values("parsed")

    #assert "value" in data_instrument['common_params']['arm_a']['sensor']['temp_nominal'], "Value type mismatch. Potentially corrupted or modified data."
	assert isinstance(data_instrument['common_params']['arm_a']['sensor']['gain'], int), "Value type mismatch. Potentially corrupted or modified data."

	return


@pytest.mark.parametrize("telescope", ["STP","test_STP"], indirect=True)
def test_default_throughput(telescope):
	obs = etsc.Observatory(telescope,2.4*u.m,36.45*u.m)
	obs.make_STP()
	flux = obs.bandpass(obs.bandpass.waveset)
	bp_non_zero = flux[flux!=0]
	waveset_non_zero = obs.bandpass.waveset[flux!=0]
	assert round(np.min(waveset_non_zero).value,2) == 6266.7, "Throughput check failed. Default filter modified or corrupt installation."
	assert round(np.max(waveset_non_zero).value,2) == 6393.29, "Throughput check failed. Default filter modified or corrupt installation."
	assert round(np.mean(bp_non_zero).value, 3) == 0.015, "Throughput check failed. Default filter modified or corrupt installation."

	return


@pytest.mark.parametrize("telescope", ["STP","test_STP"], indirect=True)
def test_sensor_initialization(telescope):
	obs = etsc.Observatory(telescope,2.4*u.m,36.45*u.m)
	obs.make_STP()
	if telescope == "UM":
		assert round(obs.plate_scale,6) == 0.016869, "Sensor check: Incorrect plate scale. Potentially corrupt or modified configuration file."
	if telescope == "STP":
		assert round(obs.plate_scale,6) == 0.008694, "Sensor check: Incorrect plate scale. Potentially corrupt or modified configuration file."


	assert obs.num_psf_pixels.value == 225, "Incorrect PSF size."

	return

@pytest.mark.parametrize("telescope", ["STP","test_STP"], indirect=True)
def test_counts(telescope):
	if telescope == "STP":
		data_telescope = config_stp.load_config_values("parsed")
		data_path_telescope = config_stp.get_data_path()
	if telescope == "test_STP":
		test_loader = utils_config.ConfigLoader('test_data/test_STP')
		data_telescope = utils_config.load_configs()
		data_path_telescope = config_stp.get_data_path()
	#if telescope == "UM":
	#	data_telescope = config_um.load_config_values("parsed")
	#	data_path_telescope = config_um.get_data_path()
	zodi_magnitude_normalization = float(data_telescope['astrophysics']['zodi']['zodi_mag_r'])
	obs = etsc.Observatory(telescope,2.4*u.m,36.45*u.m)
	obs.make_STP()
	obs.set_generic_source(1e-8,0)
	obs.set_background(background_file = None, plot=True)
	obs.make_observation(hoststarflux=-0.353, planetdeltamag=20,bg_flux=22.5,
                     flux_units='vega', plot=False,exobg_flux=21)

	#if telescope == "UM":
	#	assert round(obs.source_counts.value) == 16230700376
	#	assert round(obs.sky_counts.value) == 20
	#	assert round(obs.calc_SNR(exp_time=1.0 * u.s, int_time=1.0 * u.s)) == 127400
	#	assert round(obs.calc_req_source(10.0, int_time=1.0 * u.s, exp_time=1.0 * u.s)) == 155
	#	assert round(obs.calc_req_source(10.0, int_time=1.0 * u.s, exp_time=1.0 * u.s, magnitude=True)[0], 2) == 20.05
	#	assert round(obs.calc_int_time(1e6, exp_time=1.0*u.s).value) == 62
	#	assert round(obs.calc_saturation_time().value, 6) == 3.6e-5
	if telescope == "STP" or telescope == "test_STP":
		assert round(obs.source_counts.value, 3) == 0.703
		assert round(obs.sky_counts.value,7) == 0.0001748
		assert round(obs.calc_SNR(600.0 * u.s, 10.0*u.s),2) == 2.28
		inttimecalc,noiseterms = obs.calc_int_time(5,10*u.s)
		assert round(inttimecalc.value) == 3653.0
		assert round(obs.calc_saturation_time().value) == 2601301.0
	return


@pytest.mark.parametrize("telescope", ["STP","test_STP"], indirect=True)
def test_validate_ETC_snr_calculation(telescope):
	if telescope == "STP":
		data_telescope = config_stp.load_config_values("parsed")
		data_path_telescope = config_stp.get_data_path()
	if telescope == "test_STP":
		test_loader = utils_config.ConfigLoader('test_data/test_STP')
		data_telescope = test_loader.load_configs()
		data_path_telescope = config_stp.get_data_path()
	#if telescope == "UM":
	#	data_telescope = config_um.load_config_values("parsed")
	#	data_path_telescope = config_um.get_data_path()
	zodi_magnitude_normalization = float(data_telescope['astrophysics']['zodi']['zodi_mag_r'])
	obs = etsc.Observatory(telescope,2.4*u.m,36.45*u.m)
	obs.make_STP()
	#obs.bandpass *= SpectralElement(Box1D, amplitude=1, x_0=5500, width=1)

	test_flux_mag = 20.0
	test_host = -0.353
	test_wavelength = 6330 #    Angstroms
	obs.set_generic_source(1e-8,0)
	obs.set_background(background_file = None, plot=True)
	obs.make_observation(hoststarflux=test_host, planetdeltamag=test_flux_mag,bg_flux=22.5,
                     flux_units='vega', plot=False,exobg_flux=21)

	#bandpass_val = obs.bandpass(test_wavelength)

    #   Run independent calculations of expected source and sky counts
    #   Source counts

	C_p,C_b,M,C_zodi = Cp_Cb_M(static_params,coronagraph,target,test_flux_mag)
	

    #   Check the source count calculation from independent check is good to within 0.01 mag
	assert abs((-2.5 * np.log10(obs.source_counts.value/C_p.value))) < 0.01
    #   Check the sky count calculation from independent check is good to within 0.1 mag
	assert abs((-2.5 * np.log10(obs.sky_counts.value/C_zodi.value))) < 0.10

    #   Check the actual SNR calculation

	int_time = 600.0*u.s
	exp_time = 10.0*u.s
	snr = C_p*int_time/np.sqrt((C_p*int_time)+(C_b*int_time)+(M*int_time)**2)
	snr_etc = obs.calc_SNR(int_time, exp_time)

    #   Check SNR is good to within 0.5 %
	assert abs(1-snr_etc/snr)*100.0 < 0.5

	return

def calc_intTime(C_p, C_b, M, SNR):
    """Find the integration time to reach a required SNR given the planet and
    background count rates as well as the optical system's noise floor.


    Args:
        C_p (arraylike Quantity):
            Planet count rate (1/time units)
        C_b (arraylike Quantity):
            Background count rate (1/time units)
        M (arraylike Quantity):
            Noise floor count rate (1/time units)
        SNR (float):
            Required signal to noise ratio

    Returns:
        ~astropy.units.Quantity(~numpy.ndarray(float)):
            Integration times

    .. note::

        All infeasible integration times should be returned as NaN values

	"""

    # your code goes here:
    intTime = (C_p+C_b)/((C_p/SNR)**2 - M**2)


    # infinite and negative values are set to NAN
    intTime[np.isinf(intTime) | (intTime.value < 0.0)] = np.nan

    return intTime

# if you get stuck: a reference implementation is available in SSWYieldModelingTutorial.calc_intTime

# when you're done, test your function:
#C_p = 0.25/u.s # planet count rate photons/second (photons excluded from unit)
#C_b = 3.0/u.s # background count rate photons/second (photons excluded from unit)
#M = 0.00035671/u.s  # noise floor count rate photons/second (photons excluded from unit)
#SNR = 5
#intTimeCalc = calc_intTime(C_p, C_b, M, SNR)
#print(intTimeCalc)
# the expected output is ~1481.5 seconds


static_params = {"lam": 633*u.nm, # 550 nm central wavelength
                 "deltaLam": 12.66*u.nm, # 20% bandpass
                 "D": 2.43*u.m, # 6 meter telescope
                 "obsc": 0.0, # Primary is 10% obscured
                 "tau": 0.042, # The non-coronagraphic throughput assume Tcore and Tocc are the same for now
                 "QE": 0.657, # 90% Quantum Efficiency #assume QE within tau
                 # Zero-mag flux in photons cm^-2 nm^-1 s^-1 (photons omitted from unit):
                 #"F0": 1151/u.cm**2/u.angstrom/u.s, # Zero-magnitude flux (approximate)
                 #"F0": 702/u.cm**2/u.angstrom/u.s, # Zero-magnitude flux (approximate)
                "F0": 575/u.cm**2/u.angstrom/u.s, # Zero-magnitude flux (approximate)
                 "pixelScale": 0.00869*u.arcsec, # instantaneous field of view of each detector pixel
                 # dark current in counts/second/pixel (counts and pixels ommited from unit):
                 "darkCurrent": 0.00307/u.s,
                 "readNoise": 2.316, # read noise in electrons/pixel/read
                 "texp": 10*u.s, # single exposure time
                 "ppFac": 1/10., # post-processing factor
                }

coronagraph = {"tau_core": 0.543, # point source throughput
               "tau_occ": 0.843,  # extended source throughput
               "contrast": 1e-8, # contrast (this represents a *very* good coronagraph)
              }

target = {"mag_star": -0.353, # apparent magnitude
          "zodi": 22.5, # local zodi (units omitted as we're using this as an exponent)
          "exozodi": 21, # exozodi (assume a bit brighter than local zodi)
         }





def Cp_Cb_M(static_params, coronagraph, target, deltaMag):
	"""Calculates electron count rates for planet signal, background noise,
    and noise floor for an observation.

    Args:
        static_params (dict):
            Dictionary of static parameters:
            lam (Quantity):
                Central wavelength of observing bandpass (length unit)
            deltaLam (Quantity):
                Bandpass (length unit)
            D (Quantity):
                Telescope aperture diameter (length unit)
            obsc (float):
                Fraction of the primary aperture that is obscured by secondary and
                secondary support structures
            tau (float):
                Optical system throughput excluding effects of starlight suppression
                system
            QE (float):
                Detector quantum efficiency
            F0 (Quantity):
                Spectral flux density of zero-magnitude star in observing band
                (1/length^2/length/time unit)
            pixelScale (Quantity):
                Instantaneous field of view of each detector pixel (angle unit)
            darkCurrent (Quantity):
                Dark current in counts/second/pixel (1/time unit)
            readNoise (float):
                Read noise in electrons/pixel/read
            texp (Quantity):
                Single readout exposure time (time unit)
            ppFac (float):
                Post-processing factor

        cornagraph (dict):
            Dictionary of coronagraph parameters for this observation:
            tau_core (float):
                Throughput of starlight suppression system for point sources
            tau_occ (float):
                Throughput of starlight suppression system for infinitely extended
                sources

        target (dict):
            Dictionary of target observing parameters:
            mag_star (float):
                Apparennt magnitude of target star in observing band
            zodi (Quantity)
                Surface brightness of local zodi in units of magnitude/arcsec^2.
                Input must have units of angle^{-2}.
            exozodi (Quantity)
                Surface brightness of exozodi in units of magnitude/arcsec^2.
                Input must have units of angle^{-2}.
        deltaMag (float):
                Assumed delta magnitude of planet in observing band


    Returns:
        tuple:
            C_p (~astropy.units.Quantity(~numpy.ndarray(float))):
                Planet signal electron count rate in units of 1/s
            C_b (~astropy.units.Quantity(~numpy.ndarray(float))):
                Background noise electron count rate in units of 1/s
            M (~astropy.units.Quantity(~numpy.ndarray(float))):
                Residual starlight spatial structure (systematic error)
                in units of 1/s
	"""

    # Compute telescope collecting area:
    # this value should have units of length^2
	A = np.pi * (static_params["D"] / 2) ** 2 * (1 - static_params["obsc"])

    # compute the common factor of A*tau*deltaLam*QE
    # this value should have units of length^3
	eta = A * static_params["tau"] * static_params["deltaLam"] * static_params["QE"]
	print('Total System PS Throughput',static_params["tau"]*static_params["QE"]*coronagraph["tau_core"])

    # Compute the count rates of the planet
    # this should have units of 1/time
	C_star = static_params["F0"] * 10 ** (-0.4 * target["mag_star"])
	print('C_star',C_star)
	C_p = (C_star * 10 ** (-0.4 * deltaMag) * eta * coronagraph["tau_core"]).decompose()
	print('C_p',C_p)

    # Compute size of critically sampled photometric aperture
    # This should have units of angle^2
    # Hint: this is where that equivalencies input might be handy
	Omega = np.pi * ((static_params["lam"] / 2 / static_params["D"]) ** 2).to(
        u.arcsec**2, equivalencies=u.dimensionless_angles()
    )

    # Compute the local and exozodi count rates
    # this should have units of 1/time
	C_zodi = (
        static_params["F0"]
        * 10 ** (-0.4 * target["zodi"])
        * Omega
        / u.arcsec**2
        * eta
        * coronagraph["tau_occ"]
    ).decompose()
	print('C_zodi',C_zodi)

    # Compute the local and exozodi count rates
	C_exozodi = (
        static_params["F0"]
        * 10 ** (-0.4 * target["exozodi"])
        * Omega
        / u.arcsec**2
        * eta
        * coronagraph["tau_occ"]
    ).decompose()
	print('C_exozodi',C_exozodi)

    # Compute the count rates of the starlight residual
    # this should have units of 1/time
    
	C_sr = (
        C_star * eta * coronagraph["contrast"] * coronagraph["tau_core"]
    ).decompose()
	print('C_sr',C_sr)

    # number of detector pixels in the photometric aperture = Omega / theta^2
    # this value should be unitless
	Npix = (Omega / static_params["pixelScale"] ** 2.0).decompose().value
	Npix = 225.0

	print('Photometric Aperture Pixels',Npix)

    # Compute the dark current count rate
    # this should have units of 1/time
	C_dc = Npix*static_params['darkCurrent']
	print('C_dc',C_dc)

    # Compute the read noise count rate
    # this should have units of 1/time
	C_rn = Npix*static_params['readNoise']/static_params['texp']
	print('C_rn',C_rn)
	print('Finished determining individual terms')

    # total background signal rate
    # this should have units of 1/time
	C_b = C_sr + C_zodi + C_dc + C_rn + C_exozodi
	print('C_b',C_b)

    # compute the noise floor rate
    # this should have units of 1/tim
	M = C_sr*static_params['ppFac']
	print('M',M)
	print('Finished determining all terms')

	return C_p, C_b, M, C_zodi

def runItAll(deltaMag,SNR):
	C_p,C_b,M,C_zodi = Cp_Cb_M(static_params,coronagraph,target,deltaMag)
	#M=0
	intTime = calc_intTime(C_p,C_b,M,SNR)
	print(intTime)














