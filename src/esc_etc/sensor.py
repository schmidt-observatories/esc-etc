# src/esc_etc/sensor.py
"""Detector + non-coronagraph optical throughput for the ESC ETC.

The cumulative bandpass is assembled exactly as Observatory.make_STP did, EXCEPT
the FPM (focal-plane-mask) lambda/D throughput, which is a flat scalar and now
lives in Coronagraph.off_axis_throughput (see plan physics-fact #1).

``num_psf_pixels`` is the photometric extraction aperture (Telescope.resel,
Omega = pi (lambda/2D)^2) expressed in detector pixels, so the dark-current and
read-noise pixel count and the zodi/exozodi solid angle describe one aperture.
"""
import re
from pathlib import Path

import numpy as np
import pandas as pd
from astropy import units as u
import astropy.io.fits
import astropy.table
from scipy.interpolate import interp1d
from scipy.special import j0, j1
from synphot import SpectralElement
from synphot.models import Box1D, Empirical1D

from .meta import _MetaHolder_

WAVELENGTHS = np.arange(2000, 10000, 0.2) * u.AA

# End-of-life telescope + ESC throughput curves (QE included, FPM excluded),
# keyed by wheel slot ("R1") and by designation ("F620N").
_FILTER_DIR = Path(__file__).parent / "data" / "esc_filters_eol"
FILTERS = {}
for _f in sorted(_FILTER_DIR.glob("ESC_*_EOL.csv")):
    _slot, _name = _f.stem.split("_")[2:4]
    FILTERS[_slot] = FILTERS[_name.replace("p", ".")] = _f


def _filter_path(name):
    try:
        return FILTERS[name]
    except KeyError:
        raise ValueError(f"Unknown ESC filter {name!r}; choose from {sorted(FILTERS)}") from None


def filter_central_wavelength(name):
    """Design central wavelength from the designation, e.g. F725.9N -> 725.9 nm."""
    designation = _filter_path(name).stem.split("_")[3].replace("p", ".")
    return float(re.search(r"F([\d.]+)[NW]", designation)[1]) * u.nm


def filter_bandpass(name):
    df = pd.read_csv(_filter_path(name), skiprows=1)
    return SpectralElement(Empirical1D, points=df.iloc[:, 0].values * u.nm,
                           lookup_table=df.iloc[:, 1].values)


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


def _airy_peak_pixel_fraction(telescope, plate_scale):
    """Brightest-pixel share of a point source's in-aperture rate for an
    unobscured Airy PSF sampled at ``plate_scale`` arcsec/pix.

    Peak intensity is pi/4 of the total per (lambda/D)^2; encircled energy inside
    radius r (lambda/D units) is 1 - J0(pi r)^2 - J1(pi r)^2.
    ponytail: ignores Lyot-stop broadening and finite-pixel integration; set
    ``Sensor.peak_pixel_fraction`` from a real PSF image when one exists.
    """
    lam_d = (telescope.primary_filter / telescope.diameter_primary).to_value(
        u.arcsec, equivalencies=u.dimensionless_angles())
    r_ap = np.sqrt(telescope.resel.to_value(u.arcsec ** 2) / np.pi) / lam_d
    ee = 1 - j0(np.pi * r_ap) ** 2 - j1(np.pi * r_ap) ** 2
    return float((np.pi / 4) * (plate_scale / lam_d) ** 2 / ee)


class Sensor(_MetaHolder_):
    def __init__(self, bandpass, gain, dark_current, read_noise, well_depth,
                 pixel_size, num_pixels, sensor_area, sensor_temp, plate_scale,
                 telescope, peak_pixel_fraction=None, headroom=0.8):
        self._mutable_parameters = ["read_noise", "dark_current", "gain", "well_depth",
                                    "peak_pixel_fraction", "headroom"]
        self.bandpass = bandpass
        self.pixel_size = pixel_size
        self.num_pixels = num_pixels
        self.sensor_area = sensor_area
        self.sensor_temp = sensor_temp
        self.plate_scale = plate_scale
        self._telescope = telescope
        # One aperture for every SNR term: Omega = telescope.resel in pixels.
        self.num_psf_pixels = (telescope.resel.to_value(u.arcsec ** 2)
                               / plate_scale ** 2) * u.pix
        if peak_pixel_fraction is None:
            peak_pixel_fraction = _airy_peak_pixel_fraction(telescope, plate_scale)
        # headroom: usable fraction of full well before saturation/nonlinearity.
        # 0.8 is a safety margin, not a measured linearity limit.
        self._init_meta(gain=gain, dark_current=dark_current,
                        read_noise=read_noise, well_depth=well_depth,
                        peak_pixel_fraction=peak_pixel_fraction, headroom=headroom)

    @classmethod
    def from_config(cls, instrument_config, instrument_support_path, telescope_config,
                    telescope_support_path, telescope, arm="arm_a", filter=None):
        isp = Path(instrument_support_path)
        tsp = Path(telescope_support_path)
        cp = instrument_config["common_params"][arm]
        bandpass = filter_bandpass(filter) if filter else cls._config_bandpass(
            cp, isp, telescope_config, tsp)

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

        return cls(bandpass, gain, dark_current, read_noise, well_depth, pixel_size,
                   num_pixels, sensor_area, sensor_temp, plate_scale, telescope)

    @staticmethod
    def _config_bandpass(cp, isp, telescope_config, tsp):
        """Mirrors x generic box filter x polarizers x QE from the config files."""
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

        qe_path = isp / Path(cp["sensor"]["qe"])
        bandpass = bandpass * SpectralElement.from_file(qe_path.as_posix(), wave_unit="nm")
        return _resample_spectral_element(bandpass, WAVELENGTHS)

    @classmethod
    def from_default(cls, telescope, arm="arm_a", filter=None):
        import config_stp_esc
        import config_um
        return cls.from_config(
            instrument_config=config_stp_esc.load_config_values(),
            instrument_support_path=config_stp_esc.get_data_path(),
            telescope_config=config_um.load_config_values(),
            telescope_support_path=config_um.get_data_path(),
            telescope=telescope, arm=arm, filter=filter,
        )
