import numpy as np
import pytest

pytest.importorskip("config_stp_esc")
pytest.importorskip("config_um")

import esc_etc
import esc_etc.ExposureTimeSNRCalculatorESC


def test_snr():
    # esc_etc.esc_calc_snr returns (snr, esc); value re-derived for esc_etc
    # (the old stp_etc_esc value 2.279 does not carry over).
    snr, _esc = esc_etc.ExposureTimeSNRCalculatorESC.esc_calc_snr(
        600, 10, verbose=False, plot=False
    )
    val = 4.4545656651737255
    assert np.abs(float(snr) - val) < 1e-4, f"Expected {val}, but got {snr}"
