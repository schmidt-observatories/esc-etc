import stp_etc_esc
import stp_etc_esc.ExposureTimeSNRCalculatorESC
import numpy as np

def test_snr():
    snr = stp_etc_esc.ExposureTimeSNRCalculatorESC.esc_calc_snr(600,10,verbose=True)
    val = 2.279386813963883
    assert np.abs(snr - val) < 1e-4, f"Expected {val}, but got {snr}"
