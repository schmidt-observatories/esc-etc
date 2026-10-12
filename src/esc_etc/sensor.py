# src/esc_etc/sensor.py
"""Detector + non-coronagraph optical throughput for the ESC ETC.

The bandpass is mirrors x filter x polarizers x QE from the configuration, or
a measured ESC filter curve (``filter=``, ``lifetime=``). The FPM
(focal-plane-mask) throughput is not part of it; it lives in
Coronagraph.off_axis_throughput.

``aperture`` selects the photometric extraction aperture, and every SNR term uses
it: point sources are credited ``ee_fraction`` of their light (encircled energy of
an Airy PSF in that aperture, or the ``encircled_energy`` override), dark current
and read noise are charged over ``num_psf_pixels``, and zodi/exozodi over
``aperture_solid_angle``.

    "resel"    disk of diameter lambda/D (Telescope.resel), EE 0.46   [default]
    "optimal"  disk of radius 0.7 lambda/D, the read-noise-limited SNR optimum
    "box"      n x n pixels, n = ceil(2.44 lambda F# / pixel): the UA stp_etc_esc box
    "matched"  N_eff = 1 / sum p_i^2 pixels with EE = 1: matched-filter limit

ponytail: all fractions are for an unaberrated Airy PSF at the plate scale; set
``encircled_energy`` from the coronagraphic off-axis PSF when one exists.
"""
import re
from pathlib import Path

import numpy as np
import pandas as pd
from astropy import units as u
import astropy.io.fits
import astropy.table
from scipy.special import j0, j1
from synphot import SpectralElement
from synphot.models import Box1D, Empirical1D

from .meta import _MetaHolder_

WAVELENGTHS = np.arange(2000, 10000, 0.2) * u.AA

# Telescope + ESC throughput curves from the Pearl PLSE budget v0.4 (optics, QE,
# polarization 0.5 included; vortex off-axis factor and Lyot area EXCLUDED because
# Coronagraph and Telescope.surface apply them). Two lifetimes:
#   "eol": end of life, EOL contamination, 5% telescope + 10% ESC reserves
#   "bol": instrument delivery / beginning of life, ID contamination, no reserves
# Keyed by wheel slot ("R1") and by designation ("F620N").
_DATA = Path(__file__).parent / "data"


def _load_filters(lifetime):
    out = {}
    for f in sorted((_DATA / f"esc_filters_{lifetime}").glob(f"ESC_*_{lifetime.upper()}.csv")):
        slot, name = f.stem.split("_")[2:4]
        out[slot] = out[name.replace("p", ".")] = f
    return out


_FILTERS = {"eol": _load_filters("eol"), "bol": _load_filters("bol")}
FILTERS = _FILTERS["eol"]


def _filter_path(name, lifetime="eol"):
    if lifetime not in _FILTERS:
        raise ValueError(f"lifetime must be one of {sorted(_FILTERS)}, got {lifetime!r}")
    try:
        return _FILTERS[lifetime][name]
    except KeyError:
        raise ValueError(f"Unknown ESC filter {name!r}; choose from {sorted(FILTERS)}") from None


def filter_central_wavelength(name):
    """Design central wavelength from the designation, e.g. F725.9N -> 725.9 nm."""
    designation = _filter_path(name).stem.split("_")[3].replace("p", ".")
    return float(re.search(r"F([\d.]+)[NW]", designation)[1]) * u.nm


def filter_bandpass(name, lifetime="eol"):
    df = pd.read_csv(_filter_path(name, lifetime), skiprows=1)
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


def _ee_disk(r):
    """Airy encircled energy inside radius r (lambda/D)."""
    return 1 - j0(np.pi * r) ** 2 - j1(np.pi * r) ** 2


def _airy_fine(pix_per_lamD, half=6.0, sub=10):
    """Airy PSF sampled at 1/sub pixel over +-half lambda/D, as the fraction of
    the TOTAL (infinite-plane) flux in each cell: peak intensity pi/4 per
    (lambda/D)^2, so the samples sum to the encircled energy of the square."""
    d = 1.0 / pix_per_lamD / sub
    x = np.arange(-half, half, d) + d / 2
    X, Y = np.meshgrid(x, x)
    R = np.hypot(X, Y)
    with np.errstate(invalid="ignore", divide="ignore"):
        I = np.where(R == 0, 1.0, (2 * j1(np.pi * R) / (np.pi * R)) ** 2)
    return x, I * (np.pi / 4) * d * d


def aperture_geometry(aperture, pix_per_lamD, resel_pix):
    """(N_pix, encircled energy) of an unaberrated Airy PSF for a named aperture."""
    if aperture == "resel":
        return resel_pix, _ee_disk(np.sqrt(resel_pix / np.pi) / pix_per_lamD)
    if aperture == "optimal":
        return np.pi * (0.7 * pix_per_lamD) ** 2, _ee_disk(0.7)
    if aperture == "box":
        n = int(np.ceil(2 * 1.22 * pix_per_lamD))          # upstream calc_PSF('sq')
        x, I = _airy_fine(pix_per_lamD)
        inside = np.abs(x) < 0.5 * n / pix_per_lamD
        return float(n * n), float(I[np.ix_(inside, inside)].sum())
    if aperture == "matched":
        x, I = _airy_fine(pix_per_lamD)
        sub = round(len(x) / (2 * 6.0 * pix_per_lamD))
        m = (len(x) // sub) * sub
        P = I[:m, :m].reshape(m // sub, sub, m // sub, sub).sum(axis=(1, 3))
        return float(1.0 / np.sum(P ** 2)), 1.0
    raise ValueError(f"aperture must be one of resel, optimal, box, matched; got {aperture!r}")


class Sensor(_MetaHolder_):
    """Detector noise properties, the optical bandpass, and the photometric
    aperture (``aperture``, ``encircled_energy``) every SNR term uses.

    Mutable: ``read_noise``, ``dark_current``, ``gain``, ``well_depth``,
    ``peak_pixel_fraction`` (None = automatic), ``headroom``, ``aperture``,
    ``encircled_energy`` (None = Airy value; otherwise in ``(0, 1]``).
    """

    def __init__(self, bandpass, gain, dark_current, read_noise, well_depth,
                 pixel_size, num_pixels, sensor_area, sensor_temp, plate_scale,
                 telescope, peak_pixel_fraction=None, headroom=0.8,
                 aperture="resel", encircled_energy=None):
        self._mutable_parameters = ["read_noise", "dark_current", "gain", "well_depth",
                                    "peak_pixel_fraction", "headroom", "aperture",
                                    "encircled_energy"]
        self.bandpass = bandpass
        self.pixel_size = pixel_size
        self.num_pixels = num_pixels
        self.sensor_area = sensor_area
        self.sensor_temp = sensor_temp
        self.plate_scale = plate_scale
        self._telescope = telescope
        self._auto_peak = peak_pixel_fraction is None
        # headroom: usable fraction of full well before saturation/nonlinearity.
        # 0.8 is a safety margin, not a measured linearity limit.
        self._init_meta(gain=gain, dark_current=dark_current,
                        read_noise=read_noise, well_depth=well_depth,
                        peak_pixel_fraction=peak_pixel_fraction, headroom=headroom,
                        aperture=aperture, encircled_energy=encircled_energy)
        self._on_update(["aperture"])

    def _on_update(self, updated_keys):
        if "peak_pixel_fraction" in updated_keys:
            self._auto_peak = self.peak_pixel_fraction is None
        ee_override = self.encircled_energy
        if ee_override is not None and not 0 < ee_override <= 1:
            raise ValueError(f"encircled_energy must be in (0, 1], got {ee_override}")
        t = self._telescope
        lam_d = (t.primary_filter / t.diameter_primary).to_value(
            u.arcsec, equivalencies=u.dimensionless_angles())
        ppl = lam_d / self.plate_scale
        resel_pix = t.resel.to_value(u.arcsec ** 2) / self.plate_scale ** 2
        npix, ee = aperture_geometry(self.aperture, ppl, resel_pix)
        self.pix_per_lamD = float(ppl)
        self.num_psf_pixels = npix * u.pix
        self.aperture_solid_angle = npix * self.plate_scale ** 2 * u.arcsec ** 2
        self.ee_fraction = float(ee if self.encircled_energy is None else self.encircled_energy)
        if self._auto_peak:
            # brightest pixel: pi/4 of the total per (lambda/D)^2, relative to the
            # in-aperture rate (ponytail: Airy, no Lyot broadening or pixel integration)
            self.peak_pixel_fraction = float((np.pi / 4) / ppl ** 2 / self.ee_fraction)
            # meta keeps None: it records what was set, so a restore re-enters auto mode

    def plot_bandpass(self, **kw):
        """See :func:`esc_etc.plotting.plot_bandpass`."""
        from . import plotting
        return plotting.plot_bandpass(self, **kw)

    def plot_aperture(self, **kw):
        """See :func:`esc_etc.plotting.plot_aperture`."""
        from . import plotting
        return plotting.plot_aperture(self, **kw)

    @classmethod
    def from_config(cls, instrument_config, instrument_support_path, telescope_config,
                    telescope_support_path, telescope, arm="arm_a", filter=None,
                    lifetime="eol"):
        isp = Path(instrument_support_path)
        tsp = Path(telescope_support_path)
        cp = instrument_config["common_params"][arm]
        if lifetime not in _FILTERS:
            raise ValueError(f"lifetime must be one of {sorted(_FILTERS)}, got {lifetime!r}")
        if filter is None and lifetime != "eol":
            raise ValueError(f"lifetime={lifetime!r} needs a named filter; the generic "
                             "config bandpass has no BOL/EOL variants")
        lam_c = (filter_central_wavelength(filter) if filter else
                 u.Quantity(cp["optics"]["filter"]["lam_central"])).to(u.AA)
        if not u.isclose(lam_c, telescope.primary_filter):
            raise ValueError(
                f"filter={filter!r} ({lam_c:.0f}) does not match the telescope built for "
                f"{telescope.primary_filter:.0f}; pass the same filter= to Telescope")
        bandpass = filter_bandpass(filter, lifetime) if filter else cls._config_bandpass(
            cp, isp, telescope_config, tsp)

        # Detector
        pixel_size = (u.Quantity(cp["sensor"]["pixel_size"])).to(u.um) * (1.0 / u.pix)
        sensor_area = 962.56 * u.um * 962.56 * u.um
        gain_setting = cp["sensor"]["gain"]
        sensor_temp = cp["sensor"]["temp_nominal"] * u.Celsius

        def _interp(csv_key, names, x):
            f = isp / Path(cp["sensor"][csv_key])
            df = pd.read_csv(f.as_posix(), skiprows=1, names=names)
            # ponytail: clamps to the table ends (config_um_esc's -20 C nominal
            # sits just below the first dark-current row); extrapolate if the
            # detector tables are ever extended.
            return np.interp(x, df[names[0]], df[names[1]])

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
        # Dichroic (flat), when the config has one
        if "dichroic" in cp["optics"]:
            bandpass = bandpass * SpectralElement(
                Box1D, amplitude=cp["optics"]["dichroic"]["dichroic_throughput"], x_0=6000, width=7000)
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
    def from_default(cls, telescope, arm="arm_a", filter=None, lifetime="eol"):
        from . import uasal_config
        return cls.from_config(
            instrument_config=uasal_config.load_config_values("config_um_esc"),
            instrument_support_path=uasal_config.get_data_path("config_um_esc"),
            telescope_config=uasal_config.load_config_values("config_um"),
            telescope_support_path=uasal_config.get_data_path("config_um"),
            telescope=telescope, arm=arm, filter=filter, lifetime=lifetime,
        )
