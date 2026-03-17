import config_stp
import config_stp_esc
from stp_etc_esc import ExposureTimeSNRCalculatorESC as etsc
from astropy import units as u
from pathlib import Path
import numpy as np
import matplotlib.pyplot as plt
import matplotlib as mpl

if __name__ == '__main__':
	ESC = etsc.Observatory(telescope_name="Extrasolar Camera"
                      , telescope_diameter=6.5*u.m
                       , telescope_focal_len=97.5*u.m)

	preconfig_ESC = ESC.make_STP(subap='A',plot=False)
	psf_diameter, psf_min_num_pixels = ESC.calc_PSF()
	stp_config = config_stp.load_config_values()
	esc_config = config_stp_esc.load_config_values()
	stp_support_path = Path(config_stp.get_data_path())
	esc_support_path = Path(config_stp_esc.get_data_path())
	ESC.set_generic_source(1e-8,0,plot=False)
	zodi_model = stp_support_path / Path(stp_config['astrophysics']['zodi']['profile'])
	ESC.set_background(zodi_model.as_posix(), plot=False)
	hoststarflux = esc_config['common_params']['sources']['host']['magnitude']
	planetdeltamag = esc_config['common_params']['sources']['companion']['delta_magnitude']
	bg_flux = stp_config['astrophysics']['zodi']['zodi_mag_r']
	exobg_flux = esc_config['common_params']['sources']['exozodi']['delta_magnitude']

	ESC.make_observation(hoststarflux=hoststarflux, planetdeltamag=planetdeltamag,bg_flux=bg_flux,
                     flux_units='vega', plot=False,exobg_flux=exobg_flux)
	print('Saturation time ',ESC.calc_saturation_time())
	print('SNR for 600 s of integration time, 10 s exposures')

	ESC.calc_SNR(600*u.s,10*u.s)

	int_time,noiseterms = ESC.calc_int_time(10,10*u.s)
	print('Total Integration Time Needed for SNR = 10, 10s exposures: ',int_time)

	mpl.rc('font',family='Times')
	plt.rcParams['xtick.labelsize']=15
	plt.rcParams['ytick.labelsize']=15
	int_time5SNR = np.array([])
	int_time10SNR = np.array([])
	DC = np.array([]) #Empty arrays for storing noise values
	RN = np.array([])
	Zodi = np.array([])
	Exozodi = np.array([])
	Speckles = np.array([])
	frametimes = np.array([1.,5.,10.,30.,60.]) # in seconds, individual exposure times
	for i in np.array([1.,5.,10.,30.,60.]):

		int_time,noiseterms5 = ESC.calc_int_time(5,i*u.s) #SNR, individual frame time
		int_time10,noiseterms10 = ESC.calc_int_time(10,i*u.s) #SNR, individual frame time
		int_time5SNR = np.append(int_time5SNR,int_time.value)
		int_time10SNR = np.append(int_time10SNR,int_time10.value)
		DC = np.append(DC,noiseterms5[0]*(i))
		RN = np.append(RN,noiseterms5[1]) #Note that read noise in one frame is always the same, but your total read noise depends on how often you read out the detector
		Zodi = np.append(Zodi,noiseterms5[2]*(i))
		Exozodi = np.append(Exozodi,noiseterms5[3]*(i))
		Speckles = np.append(Speckles,noiseterms5[4]*(i))




	fig,ax = plt.subplots(1,1,figsize=(8,6))
	ax.plot(frametimes,int_time5SNR/60,label='SNR = 5',linestyle='None',marker='o',markersize=10)
	ax.plot(frametimes,int_time10SNR/60,label='SNR = 10',linestyle='None',marker='^',markersize=10)
	ax.set_xlabel('Individual Frame Time [s]',fontsize=18)
	ax.set_ylabel('Total Integration Time [min]',fontsize=18)
	ax.set_yscale('log')
	ax.legend(loc='best',fontsize=16)
	ax.set_title(r'$R$=-0.353 mag, 2% Bandpass',fontsize=18)

	fig.savefig('Time2SNR.pdf')

	fig2,ax2 = plt.subplots(1,1,figsize=(8,6))
	ax2.plot(frametimes,DC,label='Dark Current',linestyle='None',marker='o',markersize=10)
	ax2.plot(frametimes,RN,label='Read Noise',linestyle='None',marker='^',markersize=10)
	ax2.plot(frametimes,Zodi,label='Zodi',linestyle='None',marker='+',markersize=10)
	ax2.plot(frametimes,Exozodi,label='Exozodi',linestyle='None',marker='x',markersize=10)
	ax2.plot(frametimes,Speckles,label='Speckle Noise',linestyle='None',marker='*',markersize=10)
	ax2.set_xlabel('Individual Frame Times [s]',fontsize=18)
	ax2.set_ylabel('Counts',fontsize=18)
	ax2.set_yscale('log')
	ax2.legend(loc='best',fontsize=16)
	ax2.set_title(r'Noise Sources in Individual Frames to reach 5$\sigma$, 2% Bandpass',fontsize=18)

	fig2.savefig('NoiseSources_5sigma.pdf')





