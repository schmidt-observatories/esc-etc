"""Analytic coronagraph SNR engine for the ESC ETC.

Extracted verbatim from Observatory.calc_SNR / calc_int_time. This is the
default Simulation.noise_model; a future 2D-PSF image model can be swapped in
behind the same interface.

Frame accounting (issue #15): an integration of ``total_time`` is read out as
``n_reads = ceil(total_time / frame_time)`` frames -- whole frames of
``frame_time`` plus one shorter final frame -- and never fewer than one read.
Read-noise variance scales with that integer.

Reference subtraction (issue #12): with ``coronagraph.subtraction == "rdi"`` a
reference star ``beta = ref_brightness_ratio`` times brighter than the host is
observed for ``t_ref = ref_time_ratio * total_time``, scaled by
``kappa = total_time / (beta * t_ref)`` to match the target speckle counts, and
subtracted. Its random variance ``kappa**2 * var_ref`` (speckle scaled by beta;
zodi, exozodi, dark and read noise as on target) adds to the science variance.
``total_time`` is on-target science time; ``charged_time`` includes the
reference. ``"none"`` reproduces the single-image budget.
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


def _background_variance(rates, sensor, t, frame_time, star_scale=1.0):
    """Random variance (e-) of everything but the planet in a ``t`` exposure of a
    star ``star_scale`` times the host: speckle, zodi, exozodi, dark, read."""
    return (
        (star_scale * rates.speckle + rates.zodi + rates.exozodi) * t
        + sensor.dark_current * t * sensor.num_psf_pixels
        + sensor.num_psf_pixels * sensor.read_noise**2 * n_reads(t, frame_time)
    )


def _reference_variance(rates, sensor, coronagraph, total_time, frame_time):
    """Scaled random variance contributed by the subtracted reference image."""
    if coronagraph.subtraction == "none":
        return 0 * u.electron
    beta, tau = coronagraph.ref_brightness_ratio, coronagraph.ref_time_ratio
    kappa = 1.0 / (beta * tau)
    return kappa**2 * _background_variance(
        rates, sensor, tau * total_time, frame_time, star_scale=beta
    )


class AnalyticCoronagraphNoiseModel:
    def snr(self, rates, sensor, coronagraph, total_time, frame_time):
        total_time = u.Quantity(total_time, u.s)  # plain numbers are seconds
        frame_time = u.Quantity(frame_time, u.s)
        _require_positive(total_time=total_time, frame_time=frame_time)
        M = rates.speckle * coronagraph.noise_floor_factor()
        var_ref = _reference_variance(
            rates, sensor, coronagraph, total_time, frame_time
        )
        total_noise = np.sqrt(
            rates.source * total_time
            + _background_variance(rates, sensor, total_time, frame_time)
            + var_ref
            + (M * total_time) ** 2 / u.electron
        )
        snr = rates.source * total_time / total_noise
        tau = coronagraph.ref_time_ratio if coronagraph.subtraction == "rdi" else 0.0
        return {
            # legacy algebra leaves a spurious electron^(1/2) on the ratio; with
            # the times in seconds the value is the dimensionless SNR
            "snr": snr.value,
            "signal_e": (rates.source * total_time).value,
            "noise_e": total_noise.value,
            "reference_noise_e": np.sqrt(var_ref).value,
            "science_time": u.Quantity(total_time, u.s),
            "charged_time": u.Quantity(total_time, u.s) * (1 + tau),
            "M": M,
        }

    def int_time_for_snr(self, snr, rates, sensor, coronagraph, frame_time):
        """Integration time to reach ``snr``.

        ``int_time_continuous`` is the closed-form inversion treating reads as
        ``total_time / frame_time``; ``int_time`` rounds it up to whole frames,
        the shortest realizable schedule that meets ``snr``. NaN when
        unreachable (systematic floor).
        """
        frame_time = u.Quantity(frame_time, u.s)  # plain numbers are seconds
        _require_positive(snr=snr, frame_time=frame_time)
        SNR = snr * u.ct
        M = rates.speckle * coronagraph.noise_floor_factor() / u.ct
        background_counts = (
            (sensor.dark_current * sensor.num_psf_pixels)
            + rates.zodi
            + rates.exozodi
            + rates.speckle
            + (
                (sensor.read_noise * sensor.read_noise)
                * sensor.num_psf_pixels
                / frame_time
            )
        )
        # reference variance per second of science time (continuous reads)
        reference_rate = 0 * background_counts
        if coronagraph.subtraction == "rdi":
            beta, tau = coronagraph.ref_brightness_ratio, coronagraph.ref_time_ratio
            reference_rate = (
                beta * rates.speckle
                + rates.zodi
                + rates.exozodi
                + sensor.dark_current * sensor.num_psf_pixels
                + sensor.read_noise**2 * sensor.num_psf_pixels / frame_time
            ) / (beta**2 * tau)
        numerator = rates.source + background_counts + reference_rate
        denominator = (rates.source / SNR) ** 2 - M**2
        int_time = (numerator / denominator) / u.ct
        # legacy algebra leaves a spurious ct/electron on the time; value is seconds
        int_time = u.Quantity(np.atleast_1d(int_time).value, u.s)
        int_time[np.isinf(int_time) | (int_time.value < 0.0)] = np.nan
        scheduled = n_reads(int_time, frame_time) * u.Quantity(frame_time, u.s)
        noise_terms = np.array(
            [
                (sensor.dark_current * sensor.num_psf_pixels).value,
                ((sensor.read_noise**2) * sensor.num_psf_pixels / frame_time).value,
                rates.zodi.value,
                rates.exozodi.value,
                rates.speckle.value,
                u.Quantity(reference_rate).value,
            ]
        )
        return {
            "int_time": scheduled,
            "int_time_continuous": int_time,
            "noise_terms": noise_terms,
        }
