import astropy.units as u
import numpy as np

from esc_etc.noise import CountRates, AnalyticCoronagraphNoiseModel


class _Sensor:
    dark_current = 0.001 * u.electron / (u.s * u.pix)
    read_noise = 1.0 * np.sqrt(1.0 * u.electron / u.pix)
    num_pixels = 1000.0 * u.pix
    num_psf_pixels = 225.0 * u.pix
    gain = 1.0 * u.electron / u.ct


class _Coronagraph:
    def noise_floor_factor(self):
        return 0.1


def test_snr_matches_hand_computed_value():
    rates = CountRates(
        source=1.0 * u.electron / u.s,
        zodi=1e-4 * u.electron / u.s,
        exozodi=1e-4 * u.electron / u.s,
        speckle=1.0 * u.electron / u.s,
        host=1e8 * u.electron / u.s,
    )
    model = AnalyticCoronagraphNoiseModel()
    out = model.snr(rates, _Sensor(), _Coronagraph(), total_time=3600 * u.s,
                    frame_time=100 * u.s)
    assert out["snr"] > 0
    # Reproduce the calc_SNR formula independently.
    s = _Sensor()
    M = (1.0 * u.electron / u.s) * 0.1
    tt, ft = 3600 * u.s, 100 * u.s
    noise = np.sqrt(
        1.0 * u.electron / u.s * tt + 1e-4 * u.electron / u.s * tt
        + 1e-4 * u.electron / u.s * tt
        + s.dark_current * tt * s.num_psf_pixels
        + s.num_psf_pixels * (s.read_noise ** 2) * (tt / ft)
        + 1.0 * u.electron / u.s * tt
        + (M * tt) ** 2 / u.electron
    )
    expected = (1.0 * u.electron / u.s * tt / noise).value
    assert out["snr"] == np.float64(expected)
