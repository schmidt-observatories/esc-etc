"""Coronagraph-specific physics for the ESC ETC.

Owns raw dark-hole contrast, post-processing gain, planet separation, and the
off-axis (FPM) lambda/D throughput curve. The FPM throughput is a flat scalar
applied by Simulation to every count rate (plan physics-fact #1).
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
        idx = np.absolute(self._lamD - lamD_separation).argmin()
        return float(self._throughput[idx])

    def speckle_scale(self):
        delta_mag = -2.5 * np.log10(self.raw_dh_contrast)
        return 10 ** (-0.4 * delta_mag)

    def noise_floor_factor(self):
        return 1.0 / self.ppgain
