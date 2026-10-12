# tests/test_plotting_integration.py
"""One slow, config-backed test exercising the Simulation domain-object path."""
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import astropy.units as u
import numpy as np
import pytest


from esc_etc.simulation import Simulation
from esc_etc.plotting import plot_count_rates, plot_snr_vs_time, plot_aperture, plot_snr_vs_zodi


def test_count_rates_and_snr_from_simulation():
    sim = Simulation.from_default(hoststarmag=-0.353, planetdeltamag=20.0,
                                  contrast=1e-8, ppgain=10, separation=0.4)
    fig, ax = plot_count_rates(sim)
    assert len(ax.patches) == 5
    plt.close(fig)

    # small sweep to keep it fast; count rates computed once internally
    fig, ax = plot_snr_vs_time(sim, total_times=np.array([100.0, 1000.0, 3600.0]) * u.s,
                               frame_time=100 * u.s)
    assert len(ax.get_lines()[0].get_xdata()) == 3
    plt.close(fig)


def test_plot_aperture_footprint_matches_sensor_pixels():
    sim = Simulation.from_default()
    for ap, patch in [("resel", "Circle"), ("box", "Rectangle"), ("matched", "Circle")]:
        sim.update(sensor__aperture=ap)
        fig, ax = plot_aperture(sim)
        p = ax.patches[0]                      # first patch is the aperture footprint
        assert type(p).__name__ == patch
        area = p.get_width() ** 2 if patch == "Rectangle" else np.pi * p.radius ** 2
        assert area == pytest.approx(sim.sensor.num_psf_pixels.value, rel=1e-6)
        plt.close(fig)


def test_snr_vs_zodi_is_monotonic_and_zero_matches_no_zodi():
    sim = Simulation.from_default()
    fig, (ax1, ax2) = plot_snr_vs_zodi(sim, factors=(0, 1, 100), frame_time=100 * u.s)
    t = ax2.get_lines()[0].get_ydata()
    assert t[0] < t[1] < t[2]                          # more zodi, longer to SNR 5
    # factor 1 reproduces the engine's own number
    r = sim.get_int_time_for_snr(5.0, 100 * u.s)
    assert t[1] * 3600 == pytest.approx(float(r["int_time_continuous"].to_value(u.s)[0]), rel=1e-9)
    plt.close(fig)
