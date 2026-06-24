# tests/test_plotting_curves.py
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np
import astropy.units as u
import pytest
from synphot import SourceSpectrum
from synphot.models import ConstFlux1D

from esc_etc.scene import Scene, SceneElement
from esc_etc.plotting import plot_offaxis_throughput, plot_bandpass, plot_spectra


def test_offaxis_throughput_raw_path():
    seps = np.linspace(0.1, 0.5, 20)
    tput = np.linspace(0.1, 0.6, 20)
    fig, ax = plot_offaxis_throughput(separations=seps, throughputs=tput,
                                      mark_separation=False)
    assert len(ax.get_lines()[0].get_xdata()) == 20
    assert ax.get_xlabel() != "" and ax.get_ylabel() != ""
    plt.close(fig)


def test_offaxis_throughput_requires_inputs():
    with pytest.raises(ValueError):
        plot_offaxis_throughput()


def test_bandpass_raw_path():
    wave = np.linspace(400, 800, 50)  # nm
    tput = np.exp(-((wave - 600) ** 2) / (2 * 30 ** 2))
    fig, ax = plot_bandpass(wavelength=wave, throughput=tput)
    assert len(ax.get_lines()[0].get_xdata()) == 50
    assert ax.get_xlabel() != "" and ax.get_ylabel() != ""
    plt.close(fig)


def test_bandpass_requires_inputs():
    with pytest.raises(ValueError):
        plot_bandpass()


def _toy_scene():
    flat = SourceSpectrum(ConstFlux1D, amplitude=0 * u.ABmag)
    star = SceneElement("star", flat, mag=0.0)
    planet = SceneElement("planet", flat, mag=0.0, deltamag=20.0)
    zodi = SceneElement("zodi", flat, mag=22.5)
    exozodi = SceneElement("exozodi", flat, mag=21.0)
    return Scene(star, planet, zodi, exozodi)


def test_spectra_draws_one_line_per_element():
    fig, ax = plot_spectra(_toy_scene(), which=("star", "planet", "zodi"))
    assert len(ax.get_lines()) == 3
    assert ax.get_legend() is not None
    plt.close(fig)


def test_spectra_requires_scene():
    with pytest.raises(ValueError):
        plot_spectra()
