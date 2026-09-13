"""Analytic coronagraph SNR engine for the ESC ETC.

Extracted verbatim from Observatory.calc_SNR / calc_int_time. This is the
default Simulation.noise_model; a future 2D-PSF image model can be swapped in
behind the same interface.

Frame accounting (issue #15): an integration of ``total_time`` is read out as
``n_reads = ceil(total_time / frame_time)`` frames -- whole frames of
``frame_time`` plus one shorter final frame -- and never fewer than one read.
Read-noise variance scales with that integer.
"""
from dataclasses import dataclass

import numpy as np
from astropy import units as u


def _require_positive(**values):
    for name, value in values.items():
        if not np.all(np.asarray(u.Quantity(value).value) > 0):
            raise ValueError(f"{name} must be > 0, got {value}")


def n_reads(total_time, frame_time):
    """Integer number of detector reads: whole frames plus a shorter last one."""
    return np.ceil((total_time / frame_time).to_value(u.dimensionless_unscaled) - 1e-9)


@dataclass
class CountRates:
    source: u.Quantity
    zodi: u.Quantity
    exozodi: u.Quantity
    speckle: u.Quantity
    host: u.Quantity


class AnalyticCoronagraphNoiseModel:
    def snr(self, rates, sensor, coronagraph, total_time, frame_time):
        _require_positive(total_time=total_time, frame_time=frame_time)
        M = rates.speckle * coronagraph.noise_floor_factor()
        total_noise = np.sqrt(
            rates.source * total_time
            + rates.zodi * total_time
            + rates.exozodi * total_time
            + sensor.dark_current * total_time * sensor.num_psf_pixels
            + sensor.num_psf_pixels * (sensor.read_noise * sensor.read_noise)
            * n_reads(total_time, frame_time)
            + rates.speckle * total_time
            + (M * total_time) ** 2 / u.electron
        )
        snr = rates.source * total_time / total_noise
        return {
            "snr": snr.value,
            "signal_e": (rates.source * total_time).value,
            "noise_e": total_noise.value,
            "M": M,
        }

    def int_time_for_snr(self, snr, rates, sensor, coronagraph, frame_time):
        """Integration time to reach ``snr``.

        ``int_time_continuous`` is the closed-form inversion treating reads as
        ``total_time / frame_time``; ``int_time`` rounds it up to whole frames,
        the shortest realizable schedule that meets ``snr``. NaN when
        unreachable (systematic floor).
        """
        _require_positive(snr=snr, frame_time=frame_time)
        SNR = snr * u.ct
        M = rates.speckle * coronagraph.noise_floor_factor() / u.ct
        background_counts = (
            (sensor.dark_current * sensor.num_psf_pixels)
            + rates.zodi + rates.exozodi + rates.speckle
            + ((sensor.read_noise * sensor.read_noise) * sensor.num_psf_pixels
               / frame_time)
        )
        numerator = rates.source + background_counts
        denominator = (rates.source / SNR) ** 2 - M ** 2
        int_time = (numerator / denominator) / u.ct
        # legacy algebra leaves a spurious ct/electron on the time; value is seconds
        int_time = u.Quantity(np.atleast_1d(int_time).value, u.s)
        int_time[np.isinf(int_time) | (int_time.value < 0.0)] = np.nan
        scheduled = n_reads(int_time, frame_time) * u.Quantity(frame_time, u.s)
        noise_terms = np.array([
            (sensor.dark_current * sensor.num_psf_pixels).value,
            ((sensor.read_noise ** 2) * sensor.num_psf_pixels / frame_time).value,
            rates.zodi.value, rates.exozodi.value, rates.speckle.value,
        ])
        return {"int_time": scheduled, "int_time_continuous": int_time,
                "noise_terms": noise_terms}
