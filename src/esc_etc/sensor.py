# src/esc_etc/sensor.py
"""Detector + non-coronagraph optical throughput for the ESC ETC.

The cumulative bandpass is assembled exactly as Observatory.make_STP did, EXCEPT
the FPM (focal-plane-mask) lambda/D throughput, which is a flat scalar and now
lives in Coronagraph.off_axis_throughput (see plan physics-fact #1).
"""
from math import ceil, floor, sqrt
from pathlib import Path

import numpy as np
import pandas as pd
from astropy import units as u
import astropy.io.fits
import astropy.table
from scipy.interpolate import interp1d
from synphot import SourceSpectrum, SpectralElement
from synphot.models import Box1D, Empirical1D

from .meta import _MetaHolder_

WAVELENGTHS = np.arange(2000, 10000, 0.2) * u.AA


def _resample_spectral_element(S, w):
    ww, ff = S._get_arrays(wavelengths=w)
    return SpectralElement(Empirical1D, points=ww, lookup_table=ff)


def _mirror_bandpass(coating_file):
    if coating_file.endswith(".fit") or coating_file.endswith(".fits"):
        df = astropy.table.Table(astropy.io.fits.getdata(coating_file)).to_pandas()
        ww = df["WAVELENGTH"].values * u.nm
        ff = df["THROUGHPUT"].values
        return SpectralElement(Empirical1D, points=ww, lookup_table=ff)
    return SpectralElement.from_file(coating_file, wave_unit="nm")


class Sensor(_MetaHolder_):
    def __init__(self, bandpass, gain, dark_current, read_noise, well_depth,
                 pixel_size, num_pixels, sensor_area, sensor_temp, plate_scale,
                 telescope):
        self._mutable_parameters = ["read_noise", "dark_current", "gain", "well_depth"]
        self.bandpass = bandpass
        self.pixel_size = pixel_size
        self.num_pixels = num_pixels
        self.sensor_area = sensor_area
        self.sensor_temp = sensor_temp
        self.plate_scale = plate_scale
        self._telescope = telescope
        self.num_psf_pixels = None
        self._init_meta(gain=gain, dark_current=dark_current,
                        read_noise=read_noise, well_depth=well_depth)
        self.calc_psf()

    @classmethod
    def from_config(cls, instrument_config, instrument_support_path, telescope_config,
                    telescope_support_path, telescope, arm="arm_a"):
        isp = Path(instrument_support_path)
        tsp = Path(telescope_support_path)
        cp = instrument_config["common_params"][arm]
        bandpass = SpectralElement(Box1D, amplitude=1, x_0=6000, width=7000)

        # Telescope mirrors
        for key in telescope_config["telescope"]["optics"].keys():
            coating = tsp / Path(telescope_config["telescope"]["optics"][key]["coating_refl"])
            bandpass = bandpass * _mirror_bandpass(coating.as_posix())
        # ESC reflective optics
        for key in cp["optics"].keys():
            if any(s in key for s in ("oap", "flat", "sphere", "dm", "fsm")):
                coating = isp / Path(cp["optics"][key]["coating_refl"])
                bandpass = bandpass * _mirror_bandpass(coating.as_posix())
        # Generic filter
        primary_filter = u.Quantity(cp["optics"]["filter"]["lam_central"]).to("AA")
        fbw = cp["optics"]["filter"]["bandwidth"]
        bandpass = bandpass * SpectralElement(
            Box1D, amplitude=0.98, x_0=primary_filter, width=fbw * primary_filter)
        # Polarizers / wave plates (NOT the FPM)
        for key in cp["optics"].keys():
            if "lp" in key or "qwp" in key:
                coating_init = cp["optics"][key]["pol_throughput"]
                if coating_init == "none":
                    bandpass = bandpass * SpectralElement(Box1D, amplitude=0.99, x_0=6000, width=7000)
                else:
                    coating_ext = isp / Path(coating_init)
                    bandpass = bandpass * SpectralElement.from_file(
                        coating_ext.as_posix(), wave_unit="nm")
                if "lp1" in key:
                    bandpass = bandpass * SpectralElement(Box1D, amplitude=0.5, x_0=6000, width=7000)

        # Detector
        pixel_size = (u.Quantity(cp["sensor"]["pixel_size"])).to(u.um) * (1.0 / u.pix)
        sensor_area = 962.56 * u.um * 962.56 * u.um
        gain_setting = cp["sensor"]["gain"]
        sensor_temp = cp["sensor"]["temp_nominal"] * u.Celsius

        def _interp(csv_key, names, x):
            f = isp / Path(cp["sensor"][csv_key])
            df = pd.read_csv(f.as_posix(), skiprows=1, names=names)
            return interp1d(df[names[0]], df[names[1]])(x)

        gain = _interp("gain_curve", ["gain_setting", "gain"], gain_setting) * (u.electron / u.ct)
        dark_current = _interp("dark_current", ["sensor_temperature", "dark_current"],
                               sensor_temp.value) * (u.electron / (u.s * u.pix))
        read_noise = _interp("read_noise", ["gain_setting", "read_noise"], gain_setting) \
            * np.sqrt(1.0 * u.electron / u.pix)
        well_depth = _interp("well_depth", ["gain_setting", "well_depth"], gain_setting) \
            * (u.electron / u.pix)

        num_pixels = (sensor_area / (pixel_size ** 2)).to("pix2").value * u.pix
        plate_scale = (pixel_size.value * 1e-6 / telescope.diameter_primary.value
                       / telescope.f_num * 206265)

        qe_path = isp / Path(cp["sensor"]["qe"])
        bandpass = bandpass * SpectralElement.from_file(qe_path.as_posix(), wave_unit="nm")
        bandpass = _resample_spectral_element(bandpass, WAVELENGTHS)

        return cls(bandpass, gain, dark_current, read_noise, well_depth, pixel_size,
                   num_pixels, sensor_area, sensor_temp, plate_scale, telescope)

    @classmethod
    def from_default(cls, telescope, arm="arm_a"):
        import config_stp_esc
        import config_um
        return cls.from_config(
            instrument_config=config_stp_esc.load_config_values(),
            instrument_support_path=config_stp_esc.get_data_path(),
            telescope_config=config_um.load_config_values(),
            telescope_support_path=config_um.get_data_path(),
            telescope=telescope, arm=arm,
        )

    def calc_psf(self, approx_type="sq"):
        wavelength = self.bandpass.wpeak()
        psf_diameter = (2 * 1.22 * wavelength * self._telescope.f_num).to("um")
        n = ceil((psf_diameter / self.pixel_size).value)
        if approx_type.lower() in ("s", "sq", "square"):
            self.num_psf_pixels = n ** 2 * u.pix
        else:
            if n % 2 == 0:
                L = int(n / 2)
                seq = [floor(0.5 + 0.5 * sqrt(n ** 2 - (2 * y - 1) ** 2)) for y in range(1, L + 1)]
                self.num_psf_pixels = 4 * sum(seq) * u.pix
            else:
                L = int((n - 1) / 2)
                seq = [floor(1 + 0.5 * sqrt(n ** 2 - 4 * (y ** 2))) for y in range(1, L + 1)]
                self.num_psf_pixels = (1 + 4 * sum(seq)) * u.pix
        return psf_diameter, self.num_psf_pixels
