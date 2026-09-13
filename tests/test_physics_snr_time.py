"""SNR as a function of integration time, in both photon-limited and
systematic-floor-limited regimes.

Measured 2026-06-01:
  - photon-limited (contrast 1e-10, ppgain 1e6): snr(900)=10.513,
    snr(3600)=21.026 -> ratio 2.0000 = sqrt(4).
  - floor-limited (contrast 1e-7, ppgain 1): snr pinned at 0.1000 = C_p/M.
"""
import numpy as np
import pytest

pytest.importorskip("config_um_esc")
pytest.importorskip("config_um")

from physics_helpers import esc_snr


def test_snr_non_decreasing_in_exp_time():
    times = [600.0, 1200.0, 2400.0, 3600.0, 7200.0]
    snrs = [esc_snr(exp_time=t)[0] for t in times]
    # Monotonically non-decreasing (allow tiny numerical slack).
    for lo, hi in zip(snrs, snrs[1:]):
        assert hi >= lo - 1e-9


def test_sqrt_time_scaling_photon_limited():
    # Deep contrast + huge ppgain drive the systematic floor M ~ 1e-9, so the
    # planet is photon-limited and SNR ~ sqrt(exp_time).
    deep = dict(contrast=1e-10, ppgain=1e6)
    snr_900, _ = esc_snr(exp_time=900.0, **deep)
    snr_3600, _ = esc_snr(exp_time=3600.0, **deep)
    assert snr_3600 / snr_900 == pytest.approx(np.sqrt(4.0), rel=1e-3)


def test_noise_floor_ceiling_saturation():
    # Shallow contrast + no post-processing gain: M dominates, SNR saturates at
    # the analytic ceiling C_p / M and stops growing with time.
    floor = dict(contrast=1e-7, ppgain=1.0)
    snr_short, esc = esc_snr(exp_time=3600.0, **floor)
    snr_long, _ = esc_snr(exp_time=14400.0, **floor)

    # Saturated: 4x the time barely moves SNR.
    assert abs(snr_long - snr_short) / snr_short < 1e-2

    # Stays at/under the analytic systematic-floor ceiling C_p / M.
    ceiling = esc.source_counts.value / esc.speckle_counts.value / esc.ppgain
    assert snr_long <= ceiling * (1 + 1e-6)
    assert snr_long == pytest.approx(ceiling, rel=1e-2)
