# tests/test_api_equivalence.py
"""Regression grid for esc_calc_snr, and the fluent Simulation API must agree
with that shim.

test_data/legacy_snr_grid.json is a snapshot of the shim's own output, taken
by generate_legacy_grid.py and regenerated after each deliberate physics change
(see its docstring for the dates and ratios). It guards against accidental
changes, not against the pre-refactor engine, whose numbers it no longer
reproduces."""

import json
import os

import astropy.units as u
import pytest


import esc_etc.ExposureTimeSNRCalculatorESC as esc_mod
from esc_etc.simulation import Simulation

_FIXTURE = os.path.join(os.path.dirname(__file__), "test_data", "legacy_snr_grid.json")
with open(_FIXTURE) as _f:
    _LEGACY = json.load(_f)


@pytest.mark.parametrize("record", _LEGACY, ids=lambda r: str(r["params"]))
def test_new_engine_matches_legacy_grid(record):
    p = record["params"]
    snr, esc = esc_mod.esc_calc_snr(verbose=False, plot=False, **p)
    assert float(snr) == pytest.approx(record["snr"], rel=2e-3)
    assert esc.source_counts.value == pytest.approx(record["source_counts"], rel=2e-3)
    assert esc.speckle_counts.value == pytest.approx(record["speckle_counts"], rel=2e-3)
    # 1e-4: the fixture predates the exact arcsec-per-radian plate scale (2 ppm)
    assert esc.num_psf_pixels.value == pytest.approx(record["num_psf_pixels"], rel=1e-4)


def test_fluent_api_matches_shim():
    sim = Simulation.from_default(
        hoststarmag=-0.353,
        planetdeltamag=20.0,
        contrast=1e-8,
        ppgain=10,
        separation=0.4,
        bg_flux=22.5,
        exobg_flux=21.0,
    )
    fluent = sim.get_snr(total_time=3600 * u.s, frame_time=100 * u.s)["snr"]
    shim, _ = esc_mod.esc_calc_snr(
        3600, 100, separation=0.4, contrast=1e-8, ppgain=10, verbose=False, plot=False
    )
    assert fluent == pytest.approx(float(shim), rel=1e-9)


def test_shim_passes_filter_through():
    shim, esc = esc_mod.esc_calc_snr(
        3600, 100, separation=0.4, verbose=False, plot=False, filter="R1"
    )
    fluent = Simulation.from_default(separation=0.4, filter="R1").get_snr(
        total_time=3600 * u.s, frame_time=100 * u.s
    )["snr"]
    assert float(shim) == pytest.approx(float(fluent))
    assert esc._sim.telescope.primary_filter.to_value(u.nm) == pytest.approx(620)
