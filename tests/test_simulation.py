# tests/test_simulation.py
import astropy.units as u
import pytest

pytest.importorskip("config_stp_esc")
pytest.importorskip("config_um")

from esc_etc.simulation import Simulation


def test_baseline_snr_and_counts_match_anchor():
    sim = Simulation.from_default(hoststarmag=-0.353, planetdeltamag=20.0,
                                  contrast=1e-8, ppgain=10, separation=0.4,
                                  bg_flux=22.5, exobg_flux=21.0)
    rates = sim.count_rate_components()
    assert rates.source.value == pytest.approx(0.915824, rel=1e-3)
    assert rates.zodi.value == pytest.approx(2.276078e-4, rel=1e-3)
    assert rates.speckle.value == pytest.approx(0.915824, rel=1e-3)
    out = sim.get_snr(total_time=3600 * u.s, frame_time=100 * u.s)
    assert out["snr"] == pytest.approx(8.9221, rel=2e-3)


def test_noise_model_seam_is_used():
    sim = Simulation.from_default()

    class Sentinel:
        def snr(self, *a, **k):
            return {"snr": 42.0}
    sim.noise_model = Sentinel()
    assert sim.get_snr(total_time=3600 * u.s, frame_time=100 * u.s)["snr"] == 42.0
