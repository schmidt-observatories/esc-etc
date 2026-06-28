"""Analytic coronagraph SNR engine for the ESC ETC.

Extracted verbatim from Observatory.calc_SNR / calc_int_time. This is the
default Simulation.noise_model; a future 2D-PSF image model can be swapped in
behind the same interface.
"""
from dataclasses import dataclass

import numpy as np
from astropy import units as u


@dataclass
class CountRates:
    source: u.Quantity
    zodi: u.Quantity
    exozodi: u.Quantity
    speckle: u.Quantity
    host: u.Quantity


class AnalyticCoronagraphNoiseModel:
    def snr(self, rates, sensor, coronagraph, total_time, frame_time):
        M = rates.speckle * coronagraph.noise_floor_factor()
        total_noise = np.sqrt(
            rates.source * total_time
            + rates.zodi * total_time
            + rates.exozodi * total_time
            + sensor.dark_current * total_time * sensor.num_psf_pixels
            + sensor.num_psf_pixels * (sensor.read_noise * sensor.read_noise)
            * (total_time / frame_time)
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
        int_time = np.atleast_1d(int_time)
        int_time[np.isinf(int_time) | (int_time.value < 0.0)] = np.nan
        noise_terms = np.array([
            (sensor.dark_current * sensor.num_psf_pixels).value,
            ((sensor.read_noise ** 2) * sensor.num_psf_pixels / frame_time).value,
            rates.zodi.value, rates.exozodi.value, rates.speckle.value,
        ])
        return {"int_time": int_time, "noise_terms": noise_terms}
