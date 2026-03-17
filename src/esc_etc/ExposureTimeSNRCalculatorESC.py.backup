"""
ExposureTimeSNRCalculatorESC.py

This code facilitates the calculation of both exposure times/snr for a given snr/exposure time respectively.

The code contained here is derived from the HST Exposure Time calculator from the STSci website. 
Link here: https://etc.stsci.edu/etc/results/ACS.im.1813528/

A significant amount of work was done by Aaron Goldtooth, developer of the ETC for the WCC.

The code uses the synphot package developed by STSci. 
Link here: https://synphot.readthedocs.io/en/latest/
"""

from astropy import units as u
import astropy.io.fits as fits
from synphot import units, SourceSpectrum, SpectralElement, Observation
from synphot.models import BlackBodyNorm1D, GaussianFlux1D, Box1D, ConstFlux1D
import numpy as np
from numpy import sqrt
import matplotlib.pyplot as plt
import os
from scipy.interpolate import interp1d
import pandas as pd
from math import ceil, floor, log10
import config_stp
import config_stp_esc
from pathlib import Path
from datetime import datetime, timezone, date, time
from importlib.metadata import version

### Defining Classes


####################################
class Observatory:
    
    ### Create class attributes ###
    attribute = "space observatory"
    
    
    ### Create new instances of class
    def __init__(self, telescope_name, telescope_diameter, telescope_focal_len):
                
        self.name = telescope_name
        
        self.diameter_primary = telescope_diameter
        telescope_surface_area = np.pi * (0.5 * telescope_diameter)**2
        self.surf_area = telescope_surface_area
        self.lyot_stop_area = 0
        self.num_mirrors = 0
        
        self.focal_len = telescope_focal_len
        self.f_num = telescope_focal_len / telescope_diameter
        self.psf_diameter = None
        self.plate_scale = None
        self.gain = None
        self.dark_current = None
        self.read_noise = None
        self.num_pixels = None
        self.num_psf_pixels = None
        self.pixel_size = None
        self.sensor_area = None
        self.sensor_temp = None
        self.rawDH_contrast = None
        self.primary_filter = None
        
        self.sky_counts = 0
        self.well_depth = None
        
        self.bandpass = SpectralElement(Box1D, amplitude=1, x_0=9000, width=10000)
        self.precoron_bandpass = SpectralElement(Box1D, amplitude=1, x_0=9000, width=10000)
        self.coron_bandpass = SpectralElement(Box1D,amplitude=1,x_0=9000,width=10000)
        self.qe_curves = []
        self.filters = []
        self.qe_wpeak = None
        self.normal_bp = SpectralElement(Box1D,amplitude=1,x_0=9000,width=10000)
        
        self.source_spectrum = None
        self.hoststar_spectrum = None
        self.source_name = None
        self.source_z = None
        self.source_counts = None
        self.hoststar_counts = None
        self.speckle_counts = None
        self.systemLimit = None
        self.exozodi_counts = None
        
        self.background_spectrum = None
        self.background_name = None
        self.resel = None
        self.ppgain = None
        self.telescope_config = None #dictionary configs
        self.instrument_config = None
        self.telescope_SP = None #support paths
        self.instrument_SP = None
        self.telescope_config_source = None #Filenames/origins of config files
        self.instrument_config_source = None
    
    
    
    ### Class Information
    
    # Get info as strings
    
    def get_info(self):
        for key, value in self.__dict__.items():
            print(f'***__{key}={value}', '\n')
    
    # Get info as array
    
    def as_array(self):
        return np.array(list(self.__dict__.items()), dtype=object)
    
    # Get info as pandas data frame
    
    def as_df(self):
        df = pd.DataFrame(np.transpose(np.array(list(self.__dict__.items()), dtype=object)))
        df.columns = df.iloc[0]
        df = df[1:]
        return df
    
    
    
    ### Noise Settings
    
    # NOTE: need to specifiy units. Need to add code to validate units.
    
    # Set gain
    def set_gain(self, gain):
        self.gain = gain
    
    # Set dark current
    def set_dark_current(self, dark_current):
        self.dark_current = dark_current
        
    # Set read noise
    def set_read_noise(self, read_noise):
        self.read_noise = read_noise
        
    # Set number of pixels
    def set_pixels(self, num_pixels):
        self.num_pixels = num_pixels
        
    # Set number of psf pixels
    def set_psf_pixels(self, num_psf_pixels):
        self.num_psf_pixels = num_psf_pixels
    
    # Set sky counts
    def set_sky_counts(self, sky_counts):
        self.sky_counts = sky_counts

    # Set host star counts
    def set_hoststar_counts(self,hoststar_counts):
        self.hoststar_counts = hoststar_counts

    # Set raw dark hole contrast
    def set_rawDH_contrast(self,rawDH_contrast):
        self.rawDH_contrast = rawDH_contrast
    
    
    
    ### Add Spectral Elements
     
    # Add Quantum Efficiancy properties
    def add_qe_curve(self, qe_fits_file, wave_unit='angstrom', num_curves=1, plot=False):
                
        self.qe_curves.append(f"{qe_fits_file} x {num_curves}")
        
        bp = SpectralElement.from_file(qe_fits_file, wave_unit=wave_unit)

        for num in range(num_curves-1):
            bp *= SpectralElement.from_file(qe_fits_file, wave_unit=wave_unit)

        self.bandpass *= bp

        self.precoron_bandpass *= bp
        
        if plot==True:
            bp.plot()
    
    
    
    # Add Sensor
    def add_sensor(self, sensor_qe_fits_file, wave_unit='nm', num_curves=1
                   , gain_setting= 100 # (0.1 dB)
                   , sensor_temp = 0 * u.Celsius
                   , sensor_area = None
                   , sensor_pixel_size = None
                   , gain = None
                   , dark_current = None
                   , read_noise = None
                   , well_depth = None
                   , plot=False
                  ):
        
        if sensor_temp.unit != u.Celsius:
            sensor_temp.to(u.Celsius, equivalencies=u.temperature())
        
       

        wave_unit = 'nm'
            
            # physical settings
        sensor_area = 962.56*u.um * 962.56*u.um
        #sensor_pixel_size = 3.76*(u.um/u.pix)
        sensor_pixel_size = (u.Quantity(self.instrument_config['common_params']['arm_a']['sensor']['pixel_size'])).to(u.um)*(1.0/u.pix)
            
            
        gain_file = self.instrument_SP / Path(self.instrument_config['common_params']['arm_a']['sensor']['gain_curve'])  
        gain_df = pd.read_csv(gain_file.as_posix(), skiprows=1, names=['gain_setting', 'gain'])  
        gain_xlist = gain_df.gain_setting
        gain_ylist = gain_df.gain
        gain_interp = interp1d(gain_xlist, gain_ylist)
            
        gain = gain_interp(gain_setting) * (u.electron/u.ct)
            
            # dark current(sensor temperature)
        dark_current_file = self.instrument_SP / Path(self.instrument_config['common_params']['arm_a']['sensor']['dark_current'])  
        dark_current_df = pd.read_csv(dark_current_file.as_posix()
                                          , skiprows=1
                                          , names=['sensor_temperature', 'dark_current'])  # new
        dark_current_xlist = dark_current_df.sensor_temperature
        dark_current_ylist = dark_current_df.dark_current
        dark_current_interp = interp1d(dark_current_xlist, dark_current_ylist)
            
        dark_current = dark_current_interp(sensor_temp.value) * (u.electron/(u.s * u.pix))
        #dark_current /= gain  # convert electron units to counts
            
            # read noise(gain-setting)
        
        read_noise_file = self.instrument_SP / Path(self.instrument_config['common_params']['arm_a']['sensor']['read_noise'])  
        read_noise_df = pd.read_csv(read_noise_file.as_posix()
                                        , skiprows=1
                                        , names=['gain_setting', 'read_noise'])  
        read_noise_xlist = read_noise_df.gain_setting
        read_noise_ylist = read_noise_df.read_noise
        read_noise_interp = interp1d(read_noise_xlist, read_noise_ylist)
            
        read_noise = read_noise_interp(gain_setting) * sqrt(1.0*u.electron/u.pix)
        #read_noise /= gain  # convert electron units to counts
            
            # well depth(gain-setting)
        well_depth_file = self.instrument_SP / Path(self.instrument_config['common_params']['arm_a']['sensor']['well_depth']) 
        well_depth_df = pd.read_csv(well_depth_file.as_posix()
                                        , skiprows=1
                                        , names=['gain_setting', 'well_depth'])
        well_depth_xlist = well_depth_df.gain_setting
        well_depth_ylist = well_depth_df.well_depth
        well_depth_interp = interp1d(well_depth_xlist, well_depth_ylist)
            
        well_depth = well_depth_interp(gain_setting) * (u.electron/u.pix)
        #well_depth /= gain  # convert electron units to counts

        self.plate_scale = (sensor_pixel_size.value * 1e-6 /self.diameter_primary.value / self.f_num * 206265)
        
        
        
        ## For all sensors   
        self.qe_curves.append(f"{sensor_qe_fits_file} x {num_curves}")
        
        self.sensor_area = sensor_area
        self.pixel_size = sensor_pixel_size 
        
        sensor_num_pixels = sensor_area / (sensor_pixel_size**2)
        self.num_pixels = sensor_num_pixels.to('pix2').value * (u.pix)

        self.gain = gain
        self.dark_current = dark_current
        self.read_noise = read_noise
        self.well_depth = well_depth
        self.sensor_temp = sensor_temp
        bp = SpectralElement.from_file(sensor_qe_fits_file, wave_unit=u.Unit('nm'))

        for num in range(num_curves-1):
            bp *= SpectralElement.from_file(sensor_qe_fits_file, wave_unit=wave_unit)

        self.bandpass *= bp

        if plot==True:
            bp.plot()
        
        
        
    # Add mirrors
    def add_mirror(self, coating_file, num_curves=1, wave_unit='nm',plot=False):
        

        mirror_qe_fits_file = coating_file
            
        
        self.num_mirrors += num_curves
                
        self.qe_curves.append(f"{mirror_qe_fits_file} x {num_curves}")
        
        bp = SpectralElement.from_file(mirror_qe_fits_file, wave_unit=wave_unit)

        for num in range(num_curves-1):
            bp *= SpectralElement.from_file(mirror_qe_fits_file, wave_unit=wave_unit)

        self.bandpass *= bp

        self.precoron_bandpass *= bp


        
        if plot==True:
            bp.plot()
        
        
        
    # Add filter properties (from fits files). Not currently used for ESC
    def add_filter(self, filter_fits_file, wave_unit='angstrom', num_curves=1, plot=False):
        
        
        self.filters.append(f"{filter_fits_file} x {num_curves}")
        
        # catch stsynphot filters
        if '.fit' in filter_fits_file:
            filter_file_path = os.path.join('fixed_filters', filter_fits_file)
            bp = SpectralElement.from_file(filter_file_path)
            
            for num in range(num_curves-1):
                bp *= SpectralElement.from_file(filter_fits_file)

            self.bandpass *= bp
        
        # Otherwise use default filters
        else:
            bp = SpectralElement.from_filter(filter_fits_file)

            
            for num in range(num_curves-1):
                bp *= SpectralElement.from_filter(filter_fits_file)

            self.bandpass *= bp

            self.precoron_bandpass *= bp
        
        if plot==True:
            bp.plot()

    #Add a QE curve for a transmissive optic
    def add_transmissive_optic(self,transmission_fits_file,wave_unit='angstrom',num_curves=1,plot=False,coronOnly=False):
        #Adds a transmissive optic with QE from a file
        #Inputs:
            #transmission_fits_file: path to fits or csv file with columns of wavelength and transmission out of 1
            #wave_unit: string: wavelength units in fits file
            #num_curves: int: How many optic transmissions to generate (for successive optics)
            #Plot: conditional: Plots current bandpass
            #coronOnly: conditional: Adds to a coronagraph only bandpass to assess coronagraph throughput only
        self.qe_curves.append(f"{transmission_fits_file} x {num_curves}")
        bp = SpectralElement.from_file(transmission_fits_file, wave_unit=wave_unit)

        for num in range(num_curves-1):
            bp *= SpectralElement.from_file(transmission_fits_file, wave_unit=wave_unit)

        self.bandpass *= bp

        self.precoron_bandpass *= bp

        if coronOnly==True:
            self.coron_bandpass *=bp
        
        if plot==True:
            bp.plot()


    #Add generic/flat filter with constant transmission
    def add_generic_filter(self, wavelength, fbw=0.05,num_curves=1, plot=False):
        #Adds a generic, box shaped filter with 98% flat transmission
        #Inputs:
            #Wavelength: float: Central wavelength in Angstroms
            #fbw: float: Fractional filter bandwidth
            #num_curves: int: How many filter transmissions to generate (for successive filters)
            #Plot: conditional: Plots current bandpass
        self.qe_curves.append(f"{wavelength} x {num_curves}")
        bp = SpectralElement(Box1D, amplitude=0.98, x_0=wavelength, width=fbw*wavelength)

        for num in range(num_curves-1):
            bp *= SpectralElement(Box1D, amplitude=1, x_0=wavelength, width=fbw*wavelength)
        self.bandpass *=bp

        self.precoron_bandpass *= bp

        if plot==True:
            bp.plot()

    #Adds a generic, box shaped flat optic with constant transmission
    def add_generic_optic(self,reflectiv,num_curves=1,plot=False,coronOnly=False):
        #Adds a generic, box shaped optic with constant, flat transmission/reflectivity
        #Inputs:
            #reflectiv: float: Fractional reflectivity/transmission
            #num_curves: int: How many reflections/transmissions to generate (for successive optics)
            #Plot: conditional: Plots current bandpass
            #coronOnly: conditional: adds optic to a bandpass that only includes coronagraph optics
        self.qe_curves.append(f"{reflectiv} x {num_curves}")
        bp = SpectralElement(Box1D,amplitude=reflectiv,x_0=20000, width=39999)

        for num in range(num_curves-1):
            bp *= SpectralElement(Box1D,amplitude=reflectiv,x_0=20000, width=39999)
        self.bandpass *=bp
        self.precoron_bandpass *= bp
        if coronOnly==True:
            self.coron_bandpass *=bp

        if plot == True:
            bp.plot()

    def add_lamD_optic(self,throughput_fits_file,separation,num_curves=1,plot=False,coronOnly=False):
        #Adds a throughput value to the bandpass that is dependent on off-axis lambda/D separation (e.g., focal plane mask)
        #Inputs:
            #throughput_fits_file: path to fits or csv file with throughput as a function of lambda/D
            #separation: float: off-axis planet separation in units of arcseconds
            #num_curves: int: How many reflections/transmissions to generate (for successive optics)
            #Plot: conditional: Plots current bandpass
            #coronOnly: conditional: adds optic to a bandpass that only includes coronagraph optics

            #####NOTE: CURRENTLY DOES NOT INTERPOLATE THE CURVE

        #Convert separation to lambda/D
        D = self.diameter_primary
        wavelength = self.primary_filter# * u.AA
        throughput_curve = fits.getdata(throughput_fits_file)
        lamD = throughput_curve[0]
        throughput = throughput_curve[1]/100.

        lamD_single = (wavelength/D).to(u.arcsec,equivalencies=u.dimensionless_angles())
        
        #Go from separation to lambda/D

        lamD_separation = separation/lamD_single.value

        #Find nearest lambda/D and throughput value for the separation of interest. Possible consideration: interpolate the throughput curve instead?

        difference = np.absolute(lamD-lamD_separation)

        indi = difference.argmin()

        throughput_value = throughput[indi]

        self.qe_curves.append(f"{lamD_separation} x {num_curves}")

        bp = bp = SpectralElement(Box1D,amplitude=throughput_value,x_0=20000, width=39999)

        for num in range(num_curves-1):
            bp *= SpectralElement(Box1D,amplitude=throughput_value,x_0=20000, width=39999)
        self.bandpass *=bp
        if coronOnly==True:
            self.coron_bandpass *=bp

        if plot == True:
            bp.plot()


    
    
    
    # Calculate the mean PSF based on the mean wavelength of combined Spectral Elements
    # OR from a user-selected wavelength
    def calc_PSF(self, wavelength=None, approx_type='sq'):
        
        if not wavelength == None:
            psf_diameter = 2*1.22*wavelength*self.f_num
            
        else:
            
            wavelength = self.bandpass.wpeak()
            
            self.qe_wpeak = wavelength
            
            psf_diameter = (2*1.22*wavelength*self.f_num)
            
        self.psf_diameter = psf_diameter.to('um')
        
        # determine total number of pixels with the psf
        n = ceil((self.psf_diameter / self.pixel_size).value)

        
        if approx_type.lower() in ['s', 'sq', 'square']:  # Gives result of nxn square
            self.num_psf_pixels = n**2 * (u.pix)
        elif approx_type.lower() in ['c', 'circ', 'circle', 'circular']:  # Gives result of all pixels with centers within a circle of radius n
            if n%2 == 0:  # n even
                L = int(n/2)
                sequence = [floor(0.5 + 0.5*sqrt(n**2 - (2*y-1)**2)) for y in list(range(1,L+1))]
                self.num_psf_pixels = 4 * sum(sequence) * (u.pix)
            elif n%2 == 1:  # n odd
                L = int((n-1)/2)
                sequence = [floor(1 + 0.5*sqrt(n**2 - 4*(y**2))) for y in list(range(1,L+1))]
                self.num_psf_pixels = 1 + 4 * sum(sequence) * (u.pix)
            
            
        return psf_diameter, self.num_psf_pixels
        
        
  
    ### class functions ###
    
    # Create a Preconfigured Observatory using submodule at 'uasal/stp_reference_data.git'
    # NOTE: This function is "complete", meaning you would only need to add observational parameters
    # to make an observation ('set_source', 'set_background', and 'make_observation'). 
    def make_STP(self,subap = 'A',plot=False,telconfig='DEFAULT',escconfig='DEFAULT',telpath='DEFAULT',escpath='DEFAULT',contrast='spec'
                 # , left=4000 ,right=8000  # for plotting (units in angstroms)
                ):

        #Inputs:
            #subap: 'A' or 'B': Which ESC subaperture to consider. If 'A', chooses the 2.43m aperture. If 'B', chooses the 1.3m aperture.
            #plot: conditional: make plots of the bandwidth when adding every optical component
        
        # Update observatory properties based on latest specifications

        if telconfig == 'DEFAULT':

            self.telescope_config = config_stp.load_config_values()
            self.telescope_config_source = 'Config_STP'+version('config_stp')
        else:
            self.telescope_config = telconfig
            self.telescope_config_source = 'Custom Telescope'
        if escconfig == 'DEFAULT':
            self.instrument_config = config_stp_esc.load_config_values()
            self.instrument_config_source = 'Config_STP_ESC'+version('config_stp_esc')
        else:
            self.instrument_config = escconfig
            self.instrument_config_source = 'Custom Instrument'
        if telpath == 'DEFAULT':

            self.telescope_SP = Path(config_stp.get_data_path())
        else:
            self.telescope_SP = telpath
        if escpath == 'DEFAULT':
            self.instrument_SP = Path(config_stp_esc.get_data_path())
        else:
            self.instrument_SP = escpath

        if subap == 'A':
            arm_key = 'arm_a'
        elif subap == 'B':
            arm_key = 'arm_b'
            raise NotImplementedError("B arm is not implemented")
        # recalc surfarce area 
        self.diameter_primary = u.Quantity(self.instrument_config['common_params'][arm_key]['pupil']['aper_clear_OD'])
        self.surf_area          = np.pi * (0.5*self.diameter_primary)**2

        #calculate lyot stop surface area
        lyot = self.instrument_config['common_params'][arm_key]['optics']['lyot_stop']['lyot_ratio']
        self.lyot_stop_area     = np.pi * (0.5*lyot*self.diameter_primary)**2

        #recalculate the effective surface area because of the lyot stop

        self.surf_area = self.lyot_stop_area
        
        self.diameter_secondary = u.Quantity(self.telescope_config['telescope']['optics']['m2']['aper_clear_OD'])
        self.support_width      = u.Quantity(self.telescope_config['telescope']['optics']['m2']['support_width'])
        self.n_supports      = u.Quantity(self.telescope_config['telescope']['optics']['m2']['n_supports'])
        self.primary_filter     = u.Quantity(self.instrument_config['common_params'][arm_key]['optics']['filter']['lam_central'])#.to('AA').value()

        self.primary_filter = self.primary_filter.to('AA')#.value

        
        
        #self.f_num           = self.telescope_config['telescope']['general']['f_number']
        self.f_num           = self.instrument_config['common_params'][arm_key]['general']['f_number_sci_cam']
        self.focal_len          = self.f_num * self.diameter_primary
        self.rms_surf           = u.Quantity(self.telescope_config['telescope']['optics']['m1']['surface_rms'])
        self.jitter_rms         = u.Quantity(self.telescope_config['observatory']['pointing']['jitter_rms'])
        self.resel              = np.pi*(((self.primary_filter)/2/self.diameter_primary*u.radian)**2).to(u.arcsec**2,equivalencies=u.dimensionless_angles()) #Size of a resolution element. Needed for SNR calculations
        self.ppgain             = 1./self.instrument_config['common_params']['ETC']['pp_gain'] #Helpful for SNR calculations later
        
        
            
        # Add STP mirrors

        for key in self.telescope_config['telescope']['optics'].keys():
            coating = self.telescope_SP / Path(self.telescope_config['telescope']['optics'][key]['coating_refl'])
            self.add_mirror(num_curves=1,coating_file=coating.as_posix(),plot=plot)

        #Begin ESC optics. If a transmission curve is unavailable, create generic optic

        for key in self.instrument_config['common_params'][arm_key]['optics'].keys():
            if 'oap' in key or 'flat' in key or 'sphere' in key or 'dm' in key or 'fsm' in key:

                coating = self.instrument_SP / Path(self.instrument_config['common_params'][arm_key]['optics'][key]['coating_refl'])
                self.add_mirror(num_curves=1, coating_file=coating.as_posix(),plot=plot)
            


        self.add_generic_filter(self.primary_filter,fbw=self.instrument_config['common_params'][arm_key]['optics']['filter']['bandwidth'],num_curves=1,plot=plot) #filter

        #self.precoron_bandpass = self.bandpass #For saving the bandpass for non-coronagraph optics


        for key in self.instrument_config['common_params'][arm_key]['optics'].keys():
            if 'lp' in key or 'qwp' in key:
                coating_init = self.instrument_config['common_params'][arm_key]['optics'][key]['pol_throughput']
                if coating_init == 'none':
                    self.add_generic_optic(0.99,num_curves=1,plot=plot,coronOnly=False) #Quarter wave plates. Needs update: transmission curve
                else:
                    coating_ext = self.instrument_SP / Path(coating_init)
                    self.add_transmissive_optic(coating_ext.as_posix(),num_curves=1,plot=plot,wave_unit='nm',coronOnly=False) #Polarizers
                if 'lp1' in key:
                    self.add_generic_optic(0.5,num_curves=1,plot=plot,coronOnly=False) #Loss from polarization filtering
                #self.precoron_bandpass = self.bandpass #Only add in field-invariant throughputs, not the FPM
            elif 'fpm' in key:
                throughput = self.instrument_SP / Path(self.instrument_config['common_params'][arm_key]['optics'][key]['throughput'])
                self.add_lamD_optic(throughput.as_posix(),self.instrument_config['common_params']['sources']['companion']['separation'],num_curves=1,plot=plot,coronOnly=True) #VVC focal plane mask

        #self.precoron_bandpass = self.bandpass/self.coron_bandpass

        #Add detector

        sensor_path = self.instrument_SP / Path(self.instrument_config['common_params'][arm_key]['sensor']['qe'])

        self.add_sensor(sensor_path.as_posix(), wave_unit='nm', num_curves=1
                       , gain_setting= self.instrument_config['common_params'][arm_key]['sensor']['gain'] # (0.1 dB)
                       , sensor_temp = self.instrument_config['common_params'][arm_key]['sensor']['temp_nominal']*u.Celsius
                       , sensor_area = None
                       , sensor_pixel_size = None
                       , gain = None
                       , dark_current = None
                       , read_noise = None
                       , well_depth = None
                       , plot=plot
                       )

        #Choose Spec or CBE contrast


        self.set_rawDH_contrast(self.instrument_config['common_params']['ETC']['rawDH_contrast_'+contrast]) #Set the raw dark hole contrast. Needed for SNR calculations
            
        # Calculate PSF
        self.calc_PSF(wavelength=None, approx_type='sq')

    def save_nonCoronThruput(self,savedir='.',savepath='nonCoronThruput'):
        #####Save the noncoronagraphic throughput (all optics except FPM) as a .txt########
        """
        Inputs: savedir, Default: './', directory to save file in
                savepath, Default: 'nonCoronThruput', path name of data table
        """

        #Save today's date
        dateNOW = datetime.now(timezone.utc).strftime("%m/%d/%Y, %H:%M:%S")

        #Save today's date for filename

        dateTODAY = datetime.now(timezone.utc).strftime("%m_%d_%Y")

        #Save current ESC ETC version number

        etcNOW = version('etc-esc')

        #description string

        descriptor1 = "Non-Coronagraphic Throughput Constructed with "+self.telescope_config_source+", "+self.instrument_config_source

        #Bandpass peak wavelength and throughput

        wpeak = str(self.precoron_bandpass.wpeak())

        tpeak = str(self.precoron_bandpass.tpeak())

        #Bandpass full width


        width = str(self.precoron_bandpass.rectwidth())

        #Build fits file header

        headerDict = {"CTIME": (dateNOW,'Creation date and time in UTC'),
                        "V_ETC": (etcNOW, 'ESC ETC Version'),
                        "WPEAK": (wpeak, 'Wavelength of Peak Throughput'),
                        "TPEAK": (tpeak, 'Peak Throughput'),
                        "WBAND": (width, 'Full width of bandpass'),
                        "TELCONF": (self.telescope_config_source, 'Telescope configuration used'),
                        "INSCONF": (self.instrument_config_source, 'Instrument configuration used')
                        }

        finalpath = os.path.join(savedir,savepath+dateTODAY+".fits")


        self.precoron_bandpass.to_fits(finalpath,overwrite=True,pri_header=headerDict,trim_zero=True)




    
    
    # Create source for observation
    def set_source(self, source_pickles_file, source_pickles_type, source_z=0, plot=False
                   # ,left=4000 ,right=8000  # for plotting (units in angstroms)
                  ):
        
        # Source Spectrum: Pickles Modelling. This is for stars
        """
        Source: https://www.stsci.edu/hst/instrumentation/reference-data-for-calibration-and-tools/astronomical-catalogs/pickles-atlas.html

        filename        sptype    T_eff
        --------------  --------  -------
        pickles_uk_1	O5V	      39810.7
        pickles_uk_2	O9V	      35481.4
        pickles_uk_3	B0V	      28183.8
        pickles_uk_4	B1V	      22387.2
        pickles_uk_5	B3V	      19054.6
        pickles_uk_6	B5-7V	  14125.4
        pickles_uk_7	B8V	      11749.0
        pickles_uk_9	A0V	      9549.93
        pickles_uk_10	A2V	      8912.51
        pickles_uk_11	A3V	      8790.23
        pickles_uk_12	A5V	      8491.80
        pickles_uk_14	F0V	      7211.08
        pickles_uk_15	F2V	      6776.42
        pickles_uk_16	F5V	      6531.31
        pickles_uk_20	F8V	      6039.48
        pickles_uk_23	G0V	      5807.64
        pickles_uk_26	G2V	      5636.38 ***
        pickles_uk_27	G5V	      5584.70
        pickles_uk_30	G8V	      5333.35
        pickles_uk_31	K0V	      5188.00
        pickles_uk_33	K2V	      4886.52
        pickles_uk_36	K5V	      4187.94
        pickles_uk_37	K7V	      3999.45
        pickles_uk_38	M0V	      3801.89
        pickles_uk_40	M2V	      3548.13
        pickles_uk_43	M4V	      3111.72 ***
        pickles_uk_44	M5V	      2951.21
        pickles_uk_46	B2IV	  19952.6
        pickles_uk_47	B6IV	  12589.3
        pickles_uk_48	A0IV	  9727.47
        pickles_uk_49	A4-7IV	  7943.28
        pickles_uk_50	F0-2IV	  7030.72
        pickles_uk_51	F5IV	  6561.45
        pickles_uk_52	F8IV	  6151.77
        pickles_uk_53	G0IV	  5929.25
        pickles_uk_54	G2IV	  5688.53
        pickles_uk_55	G5IV	  5597.57
        pickles_uk_56	G8IV	  5308.84
        pickles_uk_57	K0IV	  5011.87
        pickles_uk_58	K1IV	  4786.30
        pickles_uk_59	K3IV	  4570.88
        pickles_uk_60	O8III	  31622.8
        pickles_uk_61	B1-2III	  19952.6
        pickles_uk_63	B5III	  14791.1
        pickles_uk_64	B9III	  11091.8
        pickles_uk_65	A0III	  9571.94
        pickles_uk_67	A5III	  8452.79
        pickles_uk_69	F0III	  7585.78
        pickles_uk_71	F5III	  6531.31
        pickles_uk_72	G0III	  5610.48
        pickles_uk_73	G5III	  5164.16
        pickles_uk_76	G8III	  5011.87
        pickles_uk_78	K0III	  4852.89
        pickles_uk_87	K3III	  4365.16
        pickles_uk_93	K5III	  4008.67
        pickles_uk_95	M0III	  3819.44
        pickles_uk_100	M5III	  3419.79
        pickles_uk_105	M10III	  2500.35
        pickles_uk_106	B2II	  15995.6
        pickles_uk_107	B5II	  12589.3
        pickles_uk_108	F0II	  7943.28
        pickles_uk_109	F2II	  7328.25
        pickles_uk_110	G5II	  5248.07
        pickles_uk_111	K0-1II	  5011.87
        pickles_uk_112	K3-4II	  4255.98
        pickles_uk_113	M3II	  3411.93
        pickles_uk_114	B0I	      26001.6
        pickles_uk_117	B5I	      13396.8
        pickles_uk_118	B8I	      11194.4
        pickles_uk_119	A0I	      9727.47
        pickles_uk_121	F0I	      7691.30
        pickles_uk_122	F5I	      6637.43
        pickles_uk_123	F8I	      6095.37
        pickles_uk_124	G0I	      5508.08
        pickles_uk_126	G5I	      5046.61
        pickles_uk_127	G8I	      4591.98
        pickles_uk_128	K2I	      4255.98
        pickles_uk_130	K4I	      3990.25
        pickles_uk_131	M2I	      3451.44
        """
        
        pickles_file_path = os.path.join('pickles_models'
                                         , source_pickles_type, source_pickles_file)

        #All of this will need to change once the location of pickles models is specified
        
        
        self.source_spectrum = SourceSpectrum.from_file(pickles_file_path + '.fits')
        self.source_spectrum.z = source_z
        self.source_name = source_pickles_file + '.fits'
        self.source_z = source_z
        
        if plot==True:
            self.source_spectrum.plot(#left=left, right=right
                                     )
    def set_generic_source(self,contrast,starMag,plot=False):
        #This is for specifying an off-axis source like a planet.
        #Inputs:
            #Contrast: float: contrast value of companion
            #starMag: Host star magnitude in magnitudes
        #Convert contrast to deltaMag
        deltaMag = -2.5*np.log10(contrast)
        sourceMag = deltaMag+starMag
        self.source_spectrum = SourceSpectrum(ConstFlux1D,amplitude=sourceMag*u.ABmag)
        #self.source_spectrum = SourceSpectrum(Blackbody1D,temperature=3000) #In case you want to do a blackbody instead
        self.source_name = str(contrast)+" Planet"
        wave = range(2000,10000,10)
        if plot==True:
            self.source_spectrum.plot(wavelengths=wave,flux_unit=u.ABmag,left=2000,right=10000)
        
    # Create background for observation. This is currently used for both the Zodi and Exozodi contributions
    # info from: https://etc.stsci.edu/etcstatic/users_guide/1_ref_9_background.html
    def set_background(self, background_file=None, plot=False
                        , left=5000 ,right=7000  # for plotting (units in angstroms)
                      ):
        #background_file = 'Background_Models/' + background_file
        #self.background_spectrum = SourceSpectrum.from_file(background_file + '.fits')

        if background_file == None:
            background_file = self.telescope_SP / Path(self.telescope_config['astrophysics']['zodi']['profile'])
            background_file = background_file.as_posix()


        self.background_spectrum = SourceSpectrum.from_file(background_file)

        #self.background_name = background_file + '.fits'
        self.background_name = background_file
        
        if plot==True:
            self.background_spectrum.plot(left=left, right=right
                                         )
    
    
    # Create observation using source and return countrate. Normalizes the flux from the source to a specified vega or AB magnitude
    def make_observation(self, hoststarflux=0, planetdeltamag=20,flux_units=units.VEGAMAG
                         , bg_flux=23, bg_flux_units=units.VEGAMAG,exobg_flux=21
                         , plot=False
                          , left=4000 ,right=8000  # for plotting (units in angstroms)
                        ):
        #Inputs:
            #hoststarflux: float: host star magnitude in magnitudes
            #planetdeltamag: float: delta mag of planet companion in magnitudes
            #flux_units: units.VEGAMAG or u.ABmag: flux normalization units
            #exobg_flux: float: magnitude of exozodi noise contribution in magnitudes
            #bg_flux: float: magnitude of zodi noise contribution in magnitudes
            #plot: conditional: plot the bandpass-convolved observation
            #left: left boundary of the observation plot in angstroms
            #right: right boundary of the observation plot in angstroms

        
        vega = SourceSpectrum.from_vega()  # For unit conversion

        #Source Observation

        
        if flux_units in ['vega', units.VEGAMAG]:

            normalization_units = (hoststarflux+planetdeltamag) * units.VEGAMAG

            #normalization_units = (self.instrument_config['common_params']['sources']['host']['magnitude']+
             #                       self.instrument_config['common_params']['sources']['companion']['delta_magnitude']) * units.VEGAMAG
            
            sp_rn = self.source_spectrum.normalize(normalization_units
                                                      , self.bandpass
                                                      , vegaspec=vega
                                                      # , force='taper'
                                                      , force='extrap'
                                                     )
        
        elif flux_units in ['AB', 'ABmag', 'AB mag', 'AB magnitude', u.ABmag]:
            
            normalization_units = (hoststarflux+planetdeltamag) * u.ABmag
            #normalization_units = (self.instrument_config['common_params']['sources']['host']['magnitude']+
             #                       self.instrument_config['common_params']['sources']['companion']['delta_magnitude']) * u.ABmag
            
            sp_rn = self.source_spectrum.normalize(normalization_units
                                                      , self.bandpass
                                                      # , vegaspec=vega
                                                      # , force='taper'
                                                      , force='extrap'
                                                     )
            
        else:
            raise NotImplementedError("User-defined source flux units not currently implemented")

        sp_obs = Observation(sp_rn, self.bandpass
                              , force='extrap'
                             )
        
        if plot==True:
            sp_obs.plot(title='Source'
                         , left=left, right=right
                    )
    
        # Get countrate for observation

        source_counts = sp_obs.countrate(area=self.surf_area) * u.electron/u.ct
        self.source_counts = source_counts

        
        # Zodi Background observation
        
        #bg_rn = self.background_spectrum.normalize( self.telescope_config['astrophysics']['zodi']['zodi_mag_r']* bg_flux_units
        #                                              , self.bandpass
        #                                              , vegaspec=vega
                                                      # , force='taper'
        #                                              , force='extrap'
        #                                             )

        johnsonv = SpectralElement.from_filter('johnson_v')

        #bg_rn = self.background_spectrum.normalize( bg_flux* bg_flux_units
        #                                              , self.bandpass
        #                                              , vegaspec=vega
        #                                              # , force='taper'
        #                                              , force='extrap'
        #                                             )

        bg_rn = self.background_spectrum.normalize( bg_flux* bg_flux_units
                                                      , johnsonv
                                                      , vegaspec=vega
                                                      # , force='taper'
                                                      , force='extrap'
                                                     )
        
        bg_obs = Observation(bg_rn, self.bandpass
                                  , force='extrap'
                                 )
        
        if plot==True:
            bg_obs.plot(title='Background'
                         , left=left, right=right
                       )
        
        # Get countrate for observation
        background_counts = bg_obs.countrate(area=self.surf_area)* u.electron/u.ct*self.resel/ u.arcsec**2 #Need to multiply by a resolution element
        self.sky_counts = background_counts

        #Exozodi background observation

        #bgexo_rn = self.background_spectrum.normalize( (self.instrument_config['common_params']['sources']['host']['magnitude']+
        #                            self.instrument_config['common_params']['sources']['exozodi']['delta_magnitude']) * bg_flux_units
        #                                              , self.bandpass
        #                                              , vegaspec=vega
                                                      # , force='taper'
        #                                              , force='extrap'
        #                                             )

        bgexo_rn = self.background_spectrum.normalize( (hoststarflux+
                                    exobg_flux) * bg_flux_units
                                                      , self.bandpass
                                                      , vegaspec=vega
                                                      # , force='taper'
                                                      , force='extrap'
                                                     )
        
        bgexo_obs = Observation(bgexo_rn, self.bandpass
                                  , force='extrap'
                                 )
        
        if plot==True:
            bgexo_obs.plot(title='Exozodi'
                         , left=left, right=right
                       )
        
        # Get countrate for observation
        exobackground_counts = bgexo_obs.countrate(area=self.surf_area)* u.electron/u.ct*self.resel/ u.arcsec**2 #Need to multiply by a resolution element
        self.exozodi_counts = exobackground_counts

        #Calculate the speckle noise contribution

        darkholecontrastToDelMag = -2.5*np.log10(self.rawDH_contrast)

        if flux_units in ['vega', units.VEGAMAG]:


            #normalization_units = (self.instrument_config['common_params']['sources']['host']['magnitude']+darkholecontrastToDelMag) * units.VEGAMAG
            normalization_units = (hoststarflux+darkholecontrastToDelMag) * units.VEGAMAG
            
            speckle_rn = self.source_spectrum.normalize(normalization_units
                                                      , self.bandpass
                                                      , vegaspec=vega
                                                      # , force='taper'
                                                      , force='extrap'
                                                     )
        
        elif flux_units in ['AB', 'ABmag', 'AB mag', 'AB magnitude', u.ABmag]:
            
            #normalization_units = (self.instrument_config['common_params']['sources']['host']['magnitude']+darkholecontrastToDelMag) * u.ABmag

            normalization_units = (hoststarflux+darkholecontrastToDelMag) * u.ABmag
            
            speckle_rn = self.source_spectrum.normalize(normalization_units
                                                      , self.bandpass
                                                      # , vegaspec=vega
                                                      # , force='taper'
                                                      , force='extrap'
                                                     )
        speckle_obs = Observation(speckle_rn, self.bandpass
                                  , force='extrap'
                                 )
        
        if plot==True:
            speckle_obs.plot(title='Speckle Noise'
                         , left=left, right=right
                       )
        speckle_counts = speckle_obs.countrate(area=self.surf_area)* u.electron/u.ct

        self.speckle_counts = speckle_counts



        
        return source_counts, background_counts,speckle_counts

    
    
    def calc_saturation_time(self):
        # NOTE: Requires setting of source and/or background and performing 'make_observation'
        return self.well_depth / ( (self.source_counts / self.num_psf_pixels) + (self.sky_counts / self.num_psf_pixels) + (self.speckle_counts / self.num_psf_pixels)+ (self.exozodi_counts / self.num_psf_pixels))
    
    
    # Calculate SNR for a given total exposure time in seconds and individual frame time in seconds
    def calc_SNR(self, int_time, exp_time):
        # NOTE: Requires setting of source and/or background and performing 'make_observation'
        
        source_counts = self.source_counts


        sky_counts = self.sky_counts
        dark_current = self.dark_current
        readout_noise = self.read_noise
        num_sky_pix = self.num_pixels
        num_psf_pix = self.num_psf_pixels
        hoststar_counts = self.hoststar_counts
        speckle_counts = self.speckle_counts
        exozodi_counts = self.exozodi_counts
        M = speckle_counts*self.ppgain

        print('Source Counts',source_counts)
        print('DC',dark_current*num_psf_pix)
        print('RN',readout_noise*readout_noise*num_psf_pix*int_time/(exp_time))
        print('Zodi',sky_counts)
        print('Exozodi',exozodi_counts)
        print('Speckles',speckle_counts)
        print('M',M)
        
        # Need to give one the following:
        gain=self.gain # [e^- / ADU]
        qeff=None # quantum efficiency (ranges from 0-1) [e^- / photon]
    
        from numpy import sqrt

        if gain!=None and qeff==None:
            # NOTE: Quantum efficiency is already taken into account for both source
            # and sky counts.

            total_noise = sqrt( source_counts*int_time 
                                  + sky_counts*int_time #zodi (resolution element already factored in)
                                  + exozodi_counts*int_time #exozodi (resolution element already factored in)
                                    + dark_current*int_time*num_psf_pix #dark
                                  + num_psf_pix*(readout_noise*readout_noise)*(int_time/exp_time) #read
                                  + speckle_counts*int_time
                                  + (M*int_time)**2/u.electron
                                 )

            snr = source_counts*int_time / total_noise

        elif qeff!=None and gain==None:

            total_noise = sqrt( source_counts*qeff*int_time 
                                  + sky_counts*qeff*int_time
                                  +exozodi_counts*qeff*int_time
                                  + dark_current*int_time*num_psf_pix 
                                  + num_psf_pix*(readout_noise*readout_noise)*(int_time/exp_time)
                                  + speckle_counts*qeff*int_time
                                  + (M*qeff*int_time)**2/u.electron
                                 )

            snr = source_counts*qeff*int_time / total_noise

        else:
            raise ValueError('No Gain or Quantum Efficiency given.')

        return snr.value
    
    
    # Calculate integration time for a given snr and individual exposure time

    def calc_int_time(self, snr, exp_time):
        # NOTE: Requires setting of source and/or background and performing 'make_observation'
        #Updated calculation
        
        SNR = snr*u.ct


        source_counts = self.source_counts


        sky_counts = self.sky_counts
        dark_current = self.dark_current
        readout_noise = self.read_noise
        num_sky_pix = self.num_pixels
        num_psf_pix = self.num_psf_pixels
        hoststar_counts = self.hoststar_counts
        speckle_counts = self.speckle_counts
        exozodi_counts = self.exozodi_counts
        M = speckle_counts*self.ppgain/u.ct
        print('DC',dark_current*num_psf_pix)
        print('RN',readout_noise*readout_noise*num_psf_pix/(exp_time))
        print('Zodi',sky_counts)
        print('Exozodi',exozodi_counts)
        print('Speckles',speckle_counts)
        print('M',M)

        
        # Need to give one the following:
        gain=self.gain # [e^- / ADU]
        qeff=None # quantum efficiency (ranges from 0-1) [e^- / photon]
    
        background_counts = (dark_current*num_psf_pix)+(sky_counts)+exozodi_counts+speckle_counts+((readout_noise*readout_noise)*num_psf_pix/(exp_time))
        numerator = source_counts+background_counts
        denominator = (source_counts/SNR)**2-M**2
        int_time = (numerator/denominator)/u.ct

        int_time[np.isinf(int_time) | (int_time.value < 0.0)] = np.nan

        noise_terms = np.array([(dark_current*num_psf_pix).value,((readout_noise**2)*num_psf_pix/(exp_time)).value,sky_counts.value,
                                exozodi_counts.value,speckle_counts.value])

        return int_time, noise_terms
        

    

        
