"""Coronagraph-specific physics for the ESC ETC.

Owns raw dark-hole contrast, post-processing gain, planet separation, and the
off-axis (FPM) lambda/D throughput curve. The FPM throughput is a flat scalar
applied by Simulation to every count rate (plan physics-fact #1).

Definitions (issue #10):

* ``off_axis_throughput`` k: fraction of an off-axis point source's photons
  transmitted by the FPM at that separation, relative to the same source with
  no coronagraph. Simulation multiplies point sources by k and, separately, by
  the aperture's encircled energy ``Sensor.ee_fraction``. The FPM FITS table
  does not record whether it is core, peak, or total throughput (issue #30).
* ``raw_dh_contrast`` C: residual stellar intensity in the dark hole divided by
  the off-axis PSF at the same separation, so stellar leakage in the aperture
  is ``R_host * C * k * EE``.
* ``ppgain``: an ASSUMED/calibrated residual-speckle suppression factor. The
  systematic floor is ``R_speckle / ppgain``. It is not a prediction of what a
  post-processing algorithm will achieve, and it carries no random-noise cost;
  that cost is modeled by the subtraction strategy below (issue #12).
* ``subtraction``: ``"none"`` (one science image, the default) or ``"rdi"``
  (reference-differential imaging). For RDI a reference star
  ``ref_brightness_ratio`` times brighter than the host is observed for
  ``ref_time_ratio`` times the science time, scaled to the target, and
  subtracted; its scaled random variance is added to the science variance
  (Nemati et al. 2023, JATIS 9, 034007). Roll/ADI self-subtraction is not
  modeled. ``total_time`` is always on-target science time; the noise model
  reports the charged time ``total_time * (1 + ref_time_ratio)`` for RDI.
"""
from pathlib import Path

import numpy as np
from astropy import units as u
import astropy.io.fits as fits

from .meta import _MetaHolder_


class Coronagraph(_MetaHolder_):
    """Raw dark-hole contrast, post-processing gain, planet separation, the FPM
    off-axis throughput curve, and the reference-subtraction strategy."""

    def __init__(self, raw_dh_contrast, ppgain, separation, primary_filter,
                 diameter_primary, lamD, throughput, subtraction="none",
                 ref_brightness_ratio=1.0, ref_time_ratio=1.0):
        self._mutable_parameters = ["raw_dh_contrast", "ppgain", "separation",
                                    "subtraction", "ref_brightness_ratio", "ref_time_ratio"]
        self.primary_filter = primary_filter
        self.diameter_primary = diameter_primary
        self._lamD = lamD
        self._throughput = throughput
        self._init_meta(raw_dh_contrast=raw_dh_contrast, ppgain=ppgain,
                        separation=separation, subtraction=subtraction,
                        ref_brightness_ratio=ref_brightness_ratio,
                        ref_time_ratio=ref_time_ratio)
        self._on_update([])

    def _on_update(self, updated_keys):
        if self.raw_dh_contrast < 0:
            raise ValueError(f"raw_dh_contrast must be >= 0, got {self.raw_dh_contrast}")
        if self.ppgain <= 0:
            raise ValueError(f"ppgain must be > 0, got {self.ppgain}")
        if self.separation <= 0:
            raise ValueError(f"separation must be > 0 arcsec, got {self.separation}")
        if self.subtraction not in ("none", "rdi"):
            raise ValueError(f"subtraction must be 'none' or 'rdi', got {self.subtraction!r}")
        if self.ref_brightness_ratio <= 0 or self.ref_time_ratio <= 0:
            raise ValueError("ref_brightness_ratio and ref_time_ratio must be > 0")

    @classmethod
    def from_config(cls, instrument_config, instrument_support_path, telescope,
                    raw_dh_contrast=1e-8, ppgain=10, separation=0.4, arm="arm_a"):
        isp = Path(instrument_support_path)
        cp = instrument_config["common_params"][arm]
        lamD = throughput = None
        for key in cp["optics"].keys():
            if "fpm" in key:
                tpath = isp / Path(cp["optics"][key]["throughput"])
                curve = fits.getdata(tpath.as_posix())
                lamD = np.asarray(curve[0])
                throughput = np.asarray(curve[1]) / 100.0
                break
        if lamD is None:
            raise ValueError("No FPM throughput entry found in instrument config optics")
        return cls(raw_dh_contrast, ppgain, separation, telescope.primary_filter,
                   telescope.diameter_primary, lamD, throughput)

    @classmethod
    def from_default(cls, telescope, raw_dh_contrast=1e-8, ppgain=10, separation=0.4,
                     arm="arm_a"):
        from . import uasal_config
        return cls.from_config(
            instrument_config=uasal_config.load_config_values("config_um_esc"),
            instrument_support_path=uasal_config.get_data_path("config_um_esc"),
            telescope=telescope, raw_dh_contrast=raw_dh_contrast, ppgain=ppgain,
            separation=separation, arm=arm,
        )

    def off_axis_throughput(self, separation=None):
        if separation is None:
            separation = self.separation
        lamD_single = (self.primary_filter / self.diameter_primary).to(
            u.arcsec, equivalencies=u.dimensionless_angles())
        lamD_separation = separation / lamD_single.value
        if not (self._lamD.min() <= lamD_separation <= self._lamD.max()):
            raise ValueError(
                f"separation {separation} arcsec = {lamD_separation:.2f} lambda/D is outside "
                f"the FPM throughput table [{self._lamD.min():.2f}, {self._lamD.max():.2f}] lambda/D")
        idx = np.absolute(self._lamD - lamD_separation).argmin()
        return float(self._throughput[idx])

    def plot_offaxis_throughput(self, **kw):
        """See :func:`esc_etc.plotting.plot_offaxis_throughput`."""
        from . import plotting
        return plotting.plot_offaxis_throughput(self, **kw)

    def speckle_scale(self):
        """Stellar-leakage rate in the extraction aperture per unit host rate."""
        return self.raw_dh_contrast

    def noise_floor_factor(self):
        return 1.0 / self.ppgain
