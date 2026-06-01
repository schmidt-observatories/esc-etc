"""Thin runnable wrapper around the canonical esc_calc_snr().

The SNR calculation lives in esc_etc.ExposureTimeSNRCalculatorESC. Keeping a
separate copy here caused it to drift out of sync with the package (it was
missing the `separation`/`ppgain` arguments), so this script now just calls the
package version directly.
"""
from esc_etc.ExposureTimeSNRCalculatorESC import esc_calc_snr

if __name__ == '__main__':
    exp_time = 600
    int_time = 10

    # Calculate SNR
    snr, esc = esc_calc_snr(exp_time, int_time, verbose=True)
    print(f"SNR: {snr}")
