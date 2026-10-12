"""Reference-differential imaging noise and time accounting (issue #12)."""
import astropy.units as u
import numpy as np
import pytest


from esc_etc import Simulation

T, FT = 3600 * u.s, 100 * u.s


def _background_var(sim, t, star_scale=1.0):
    r, s = sim.count_rate_components(), sim.sensor
    return ((star_scale * r.speckle + r.zodi + r.exozodi) * t
            + s.dark_current * t * s.num_psf_pixels
            + s.num_psf_pixels * s.read_noise ** 2 * np.ceil((t / FT).value)).value


def test_none_is_single_image_and_rdi_adds_hand_computed_reference_variance():
    sim = Simulation.from_default()
    none = sim.get_snr(T, FT)
    assert none["reference_noise_e"] == 0 and none["charged_time"] == T

    # equal-brightness reference for equal time: kappa = 1, var_ref = background var
    sim.update(coronagraph__subtraction="rdi")
    rdi = sim.get_snr(T, FT)
    assert rdi["noise_e"] ** 2 - none["noise_e"] ** 2 == pytest.approx(_background_var(sim, T), rel=1e-9)
    assert rdi["reference_noise_e"] ** 2 == pytest.approx(_background_var(sim, T), rel=1e-9)
    assert rdi["charged_time"] == 2 * T and rdi["science_time"] == T
    assert rdi["snr"] < none["snr"]

    # 10x brighter reference for twice the time: kappa = 1/20, speckle scaled by 10
    sim.update(coronagraph__ref_brightness_ratio=10.0, coronagraph__ref_time_ratio=2.0)
    bright = sim.get_snr(T, FT)
    expected = (1 / 20.0) ** 2 * _background_var(sim, 2 * T, star_scale=10.0)
    assert bright["reference_noise_e"] ** 2 == pytest.approx(expected, rel=1e-9)
    assert bright["reference_noise_e"] < rdi["reference_noise_e"]
    assert bright["charged_time"] == 3 * T


def test_int_time_round_trips_under_rdi():
    sim = Simulation.from_default()
    sim.update(coronagraph__subtraction="rdi", coronagraph__ref_brightness_ratio=3.0)
    snr = sim.get_snr(T, FT)["snr"]
    out = sim.get_int_time_for_snr(snr, frame_time=FT)
    assert out["int_time"][0].value == pytest.approx(3600.0)
    assert out["noise_terms"][-1] > 0  # reference contribution exposed


def test_invalid_strategy_fails_loudly():
    sim = Simulation.from_default()
    with pytest.raises(ValueError, match="subtraction"):
        sim.update(coronagraph__subtraction="adi")
    assert sim.coronagraph.subtraction == "none"
