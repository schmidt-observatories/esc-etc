# tests/test_api_equivalence.py
"""The new OO engine must reproduce the frozen legacy grid, and the fluent
Simulation API must agree with the esc_calc_snr shim."""
import json
import os

import astropy.units as u
import pytest

pytest.importorskip("config_stp_esc")
pytest.importorskip("config_um")

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
    assert esc.num_psf_pixels.value == pytest.approx(record["num_psf_pixels"])


def test_fluent_api_matches_shim():
    sim = Simulation.from_default(hoststarmag=-0.353, planetdeltamag=20.0,
                                  contrast=1e-8, ppgain=10, separation=0.4,
                                  bg_flux=22.5, exobg_flux=21.0)
    fluent = sim.get_snr(total_time=3600 * u.s, frame_time=100 * u.s)["snr"]
    shim, _ = esc_mod.esc_calc_snr(3600, 100, separation=0.4, contrast=1e-8,
                                   ppgain=10, verbose=False, plot=False)
    assert fluent == pytest.approx(float(shim), rel=1e-9)
