# tests/test_simulation.py
import astropy.units as u
import pytest


from esc_etc.simulation import Simulation


def test_baseline_snr_and_counts_match_anchor():
    sim = Simulation.from_default(
        hoststarmag=-0.353,
        planetdeltamag=20.0,
        contrast=1e-8,
        ppgain=10,
        separation=0.4,
        bg_flux=22.5,
        exobg_flux=21.0,
    )
    rates = sim.count_rate_components()
    assert rates.source.value == pytest.approx(2.479242, rel=1e-3)
    assert rates.zodi.value == pytest.approx(8.646151e-04, rel=1e-3)
    assert rates.speckle.value == pytest.approx(2.479242, rel=1e-3)
    out = sim.get_snr(total_time=3600 * u.s, frame_time=100 * u.s)
    assert out["snr"] == pytest.approx(9.87424, rel=2e-3)


def test_noise_model_seam_is_used():
    sim = Simulation.from_default()

    class Sentinel:
        def snr(self, *a, **k):
            return {"snr": 42.0}

    sim.noise_model = Sentinel()
    assert sim.get_snr(total_time=3600 * u.s, frame_time=100 * u.s)["snr"] == 42.0


def test_int_time_round_trips_against_snr():
    import numpy as np

    sim = Simulation.from_default(
        hoststarmag=-0.353,
        planetdeltamag=20.0,
        contrast=1e-8,
        ppgain=10,
        separation=0.4,
        bg_flux=22.5,
        exobg_flux=21.0,
    )
    snr_val = sim.get_snr(total_time=3600 * u.s, frame_time=100 * u.s)["snr"]
    out = sim.get_int_time_for_snr(snr_val, frame_time=100 * u.s)
    it = out["int_time"]
    # int_time_for_snr returns an atleast_1d Quantity; extract scalar value in seconds
    val = float(np.atleast_1d(getattr(it, "value", it))[0])
    assert val == pytest.approx(3600.0, rel=1e-3)


def test_is_saturated_matches_saturation_time():
    sim = Simulation.from_default()
    st = sim.saturation_time()
    assert bool(sim.is_saturated(2 * st)) is True
    assert bool(sim.is_saturated(0.5 * st)) is False
