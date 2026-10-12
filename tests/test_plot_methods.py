"""plot_* methods on Simulation and its components, sim.plot() overview,
the sweep= keyword of plot_snr_vs_time, and is_saturated with plain floats."""
import astropy.units as u
import matplotlib.pyplot as plt
from matplotlib.figure import Figure
import numpy as np
import pytest

import esc_etc
from esc_etc import Simulation

SIM_PLOTS = ["plot_count_rates", "plot_snr_vs_time", "plot_bandpass", "plot_spectra",
             "plot_offaxis_throughput", "plot_aperture"]


@pytest.fixture(scope="module")
def sim():
    return Simulation.from_default()


@pytest.mark.parametrize("name", SIM_PLOTS)
def test_simulation_plot_method_returns_fig_ax_and_respects_ax(sim, name):
    fig, ax = getattr(sim, name)()
    assert isinstance(fig, Figure)
    plt.close(fig)
    _, mine = plt.subplots()
    fig2, ax2 = getattr(sim, name)(ax=mine)
    assert ax2 is mine
    plt.close(fig2)


@pytest.mark.parametrize("obj, name", [
    ("sensor", "plot_bandpass"), ("sensor", "plot_aperture"),
    ("coronagraph", "plot_offaxis_throughput"), ("scene", "plot_spectra"),
])
def test_component_plot_method_respects_ax(sim, obj, name):
    _, mine = plt.subplots()
    fig, ax = getattr(getattr(sim, obj), name)(ax=mine)
    assert ax is mine
    assert ax.has_data()
    plt.close(fig)


def test_overview_plot_fills_a_2x3_grid(sim):
    fig, axes = sim.plot()
    assert axes.shape == (2, 3)
    assert all(ax.has_data() for ax in axes.flat)
    plt.close(fig)


def test_snr_vs_time_sweep_draws_one_curve_per_value_and_restores(sim):
    before = sim.coronagraph.raw_dh_contrast
    fig, ax = sim.plot_snr_vs_time(sweep={"coronagraph__raw_dh_contrast": [1e-7, 1e-8, 1e-9]})
    lines = ax.get_lines()
    assert len(lines) == 3
    assert sim.coronagraph.raw_dh_contrast == before        # sweep leaves no trace
    # lower contrast -> higher SNR at the longest time
    last = [l.get_ydata()[-1] for l in lines]
    assert last[0] < last[1] < last[2]
    # the swept curve at the current value equals the unswept curve
    fig0, ax0 = sim.plot_snr_vs_time()
    np.testing.assert_allclose(lines[1].get_ydata(), ax0.get_lines()[0].get_ydata())
    assert "1e-09" in ax.get_legend().get_texts()[2].get_text()
    plt.close(fig); plt.close(fig0)


def test_snr_vs_time_sweep_reaches_nested_scene_parameters(sim):
    fig, ax = sim.plot_snr_vs_time(sweep={"scene__zodi__mag": [22.5, 17.5]})
    y = [l.get_ydata()[-1] for l in ax.get_lines()]
    assert y[1] < y[0]                                      # brighter zodi, lower SNR
    plt.close(fig)


def test_plot_snr_vs_zodi_is_gone():
    assert not hasattr(esc_etc, "plot_snr_vs_zodi")


def test_is_saturated_accepts_plain_float_seconds(sim):
    assert sim.is_saturated(100.0) == sim.is_saturated(100 * u.s)
    assert bool(sim.is_saturated(1e9)) is True
