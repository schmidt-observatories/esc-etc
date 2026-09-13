"""DEPRECATED compatibility shim.

The ESC ETC is now a compositional OO package (esc_etc.simulation.Simulation and
its components). This module preserves the historical procedural API by building
the new objects under the hood. Prefer `from esc_etc import Simulation`.
"""
import warnings

from astropy import units as u

from .simulation import Simulation
from synphot import SourceSpectrum, SpectralElement
from synphot.models import Empirical1D


def resample_SpectralElement(S, w, verbose=True, label=""):
    ww, ff = S._get_arrays(wavelengths=w)
    return SpectralElement(Empirical1D, points=ww, lookup_table=ff)


def resample_SourceSpectrum(S, w, verbose=True, label=""):
    ww, ff = S._get_arrays(wavelengths=w)
    return SourceSpectrum(Empirical1D, points=ww, lookup_table=ff)


class Observatory:
    """Thin read-only view over a Simulation, exposing the legacy count attributes."""

    def __init__(self, simulation):
        self._sim = simulation
        rates = simulation.count_rate_components()
        self.source_counts = rates.source
        self.sky_counts = rates.zodi
        self.exozodi_counts = rates.exozodi
        self.speckle_counts = rates.speckle
        self.hoststar_counts = rates.host
        self.num_psf_pixels = simulation.sensor.num_psf_pixels
        self.num_pixels = simulation.sensor.num_pixels
        self.dark_current = simulation.sensor.dark_current
        self.read_noise = simulation.sensor.read_noise
        self.gain = simulation.sensor.gain
        self.well_depth = simulation.sensor.well_depth
        # legacy: self.ppgain stored the INVERTED gain (1/ppgain)
        self.ppgain = simulation.coronagraph.noise_floor_factor()
        self.background_name = simulation.telescope.zodi_profile_path

    def calc_saturation_time(self):
        """Delegate to Simulation.saturation_time() for legacy callers."""
        return self._sim.saturation_time()


def esc_calc_snr(exp_time, int_time, hoststarmag=-0.353, contrast=1e-8,
                 planetdeltamag=20, bg_flux=22.5, exobg_flux=21,
                 flux_units="vega", separation=0.2, ppgain=10, verbose=True,
                 plot=False):
    """Build the OO Simulation and compute SNR, preserving legacy semantics.

    Historical time mapping (plan physics-fact #5): total integration time is
    this function's `exp_time`; per-frame time is `int_time`.
    """
    if verbose:
        warnings.warn(
            "esc_calc_snr/Observatory are deprecated; use esc_etc.Simulation.",
            DeprecationWarning, stacklevel=2,
        )
    sim = Simulation.from_default(
        hoststarmag=hoststarmag, planetdeltamag=planetdeltamag, contrast=contrast,
        ppgain=ppgain, separation=separation, bg_flux=bg_flux, exobg_flux=exobg_flux,
        mag_system=flux_units,
    )
    out = sim.get_snr(total_time=exp_time * u.s, frame_time=int_time * u.s)
    return out["snr"], Observatory(sim)
