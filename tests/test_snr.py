import esc_etc
import esc_etc.ExposureTimeSNRCalculatorESC
import numpy as np

def test_snr():
    snr, _ = esc_etc.ExposureTimeSNRCalculatorESC.esc_calc_snr(600,10,verbose=True)
    val = 2.279386813963883
    assert np.abs(snr - val) < 1e-4, f"Expected {val}, but got {snr}"
