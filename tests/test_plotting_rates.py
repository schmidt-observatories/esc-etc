# tests/test_plotting_rates.py
import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt
import matplotlib.colors as mcolors
import numpy as np
import astropy.units as u
import pytest

from esc_etc.noise import CountRates
from esc_etc.plotting import plot_count_rates, plot_snr_vs_time, TEAL


class _Sensor:
    dark_current = 0.001 * u.electron / (u.s * u.pix)
    num_psf_pixels = 225.0 * u.pix


def _rates():
    e = u.electron / u.s
    return CountRates(
        source=0.9 * e, zodi=2.3e-4 * e, exozodi=1e-4 * e, speckle=0.9 * e, host=9e7 * e
    )


def test_count_rates_raw_path_draws_five_bars():
    fig, ax = plot_count_rates(rates=_rates(), sensor=_Sensor())
    assert len(ax.patches) == 5
    assert ax.get_ylabel() != ""
    # first bar uses the lazuli TEAL
    assert ax.patches[0].get_facecolor() == mcolors.to_rgba(TEAL)
    assert ax.get_yscale() == "log"
    plt.close(fig)


def test_count_rates_requires_inputs():
    with pytest.raises(ValueError):
        plot_count_rates()  # no sim, no rates


def test_snr_vs_time_raw_path_plots_supplied_arrays():
    times = np.array([10.0, 100.0, 1000.0]) * u.s
    snrs = np.array([1.0, 5.0, 9.0])
    fig, ax = plot_snr_vs_time(total_times=times, snrs=snrs)
    line = ax.get_lines()[0]
    assert len(line.get_xdata()) == 3
    assert ax.get_xscale() == "log" and ax.get_yscale() == "log"
    assert ax.get_xlabel() != "" and ax.get_ylabel() != ""
    plt.close(fig)


def test_snr_vs_time_requires_inputs():
    with pytest.raises(ValueError):
        plot_snr_vs_time()  # no sim, no snrs
