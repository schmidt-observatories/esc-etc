# src/esc_etc/telescope.py
"""Telescope geometry for the ESC ETC.

Holds aperture/collecting-area geometry. Throughput lives in Sensor (mirroring
wcc-etc). Values are extracted from config_um (telescope) + config_um_esc
(per-arm aperture), matching the original Observatory.make_STP logic.
"""
from pathlib import Path

import numpy as np
from astropy import units as u

from .meta import _MetaHolder_
from .sensor import filter_central_wavelength


class Telescope(_MetaHolder_):
    def __init__(self, diameter_primary, surface, f_num, focal_len, primary_filter,
                 resel, diameter_secondary, jitter_rms, zodi_profile_path):
        self._mutable_parameters = []  # geometry is fixed post-config
        self.diameter_primary = diameter_primary
        self.surface = surface
        self.f_num = f_num
        self.focal_len = focal_len
        self.primary_filter = primary_filter
        self.resel = resel
        self.diameter_secondary = diameter_secondary
        self.jitter_rms = jitter_rms
        self.zodi_profile_path = zodi_profile_path
        self._init_meta()

    @classmethod
    def from_config(cls, telescope_config, instrument_config, telescope_support_path,
                    arm="arm_a", filter=None):
        cp = instrument_config["common_params"][arm]
        diameter_primary = u.Quantity(cp["pupil"]["aper_clear_OD"])
        lyot = cp["optics"]["lyot_stop"]["lyot_ratio"]
        surface = np.pi * (0.5 * lyot * diameter_primary) ** 2
        diameter_secondary = u.Quantity(
            telescope_config["telescope"]["optics"]["m2"]["aper_clear_OD"])
        primary_filter = (filter_central_wavelength(filter) if filter else
                          u.Quantity(cp["optics"]["filter"]["lam_central"])).to("AA")
        f_num = cp["general"]["f_number_sci_cam"]
        focal_len = f_num * diameter_primary
        jitter_rms = u.Quantity(
            telescope_config["observatory"]["pointing"]["jitter_rms"])
        # Photometric extraction aperture: a disk of diameter lambda/D. Shared by
        # the background solid angle (Simulation) and detector pixel count (Sensor).
        resel = np.pi * (((primary_filter) / 2 / diameter_primary * u.radian) ** 2).to(
            u.arcsec ** 2, equivalencies=u.dimensionless_angles())
        zodi_profile_path = (
            Path(telescope_support_path)
            / Path(telescope_config["astrophysics"]["zodi"]["profile"])
        ).as_posix()
        return cls(diameter_primary, surface, f_num, focal_len, primary_filter,
                   resel, diameter_secondary, jitter_rms, zodi_profile_path)

    @classmethod
    def from_default(cls, arm="arm_a", filter=None):
        import config_um_esc
        import config_um
        return cls.from_config(
            telescope_config=config_um.load_config_values(),
            instrument_config=config_um_esc.load_config_values(),
            telescope_support_path=config_um.get_data_path(),
            arm=arm, filter=filter,
        )
