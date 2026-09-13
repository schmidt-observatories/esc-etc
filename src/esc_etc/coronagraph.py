"""Coronagraph-specific physics for the ESC ETC.

Owns raw dark-hole contrast, post-processing gain, planet separation, and the
off-axis (FPM) lambda/D throughput curve. The FPM throughput is a flat scalar
applied by Simulation to every count rate (plan physics-fact #1).

Definitions (issue #10):

* ``off_axis_throughput`` k: fraction of an off-axis point source's photons that
  land in the extraction aperture (Telescope.resel), relative to the same source
  with no coronagraph. Encircled energy is folded into k; no separate factor is
  applied. The FPM FITS table does not record whether it is core, peak, or total
  throughput; core throughput is the assumption used here.
* ``raw_dh_contrast`` C: residual stellar intensity in the dark hole divided by
  the off-axis PSF at the same separation, both in the extraction aperture, so
  stellar leakage in the aperture is ``R_host * C * k``.
"""
from pathlib import Path

import numpy as np
from astropy import units as u
import astropy.io.fits as fits

from .meta import _MetaHolder_


class Coronagraph(_MetaHolder_):
    def __init__(self, raw_dh_contrast, ppgain, separation, primary_filter,
                 diameter_primary, lamD, throughput):
        self._mutable_parameters = ["raw_dh_contrast", "ppgain", "separation"]
        self.primary_filter = primary_filter
        self.diameter_primary = diameter_primary
        self._lamD = lamD
        self._throughput = throughput
        self._init_meta(raw_dh_contrast=raw_dh_contrast, ppgain=ppgain,
                        separation=separation)
        self._on_update([])

    def _on_update(self, updated_keys):
        if self.raw_dh_contrast < 0:
            raise ValueError(f"raw_dh_contrast must be >= 0, got {self.raw_dh_contrast}")
        if self.ppgain <= 0:
            raise ValueError(f"ppgain must be > 0, got {self.ppgain}")
        if self.separation <= 0:
            raise ValueError(f"separation must be > 0 arcsec, got {self.separation}")

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
        import config_stp_esc
        return cls.from_config(
            instrument_config=config_stp_esc.load_config_values(),
            instrument_support_path=config_stp_esc.get_data_path(),
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

    def speckle_scale(self):
        """Stellar-leakage rate in the extraction aperture per unit host rate."""
        return self.raw_dh_contrast

    def noise_floor_factor(self):
        return 1.0 / self.ppgain
