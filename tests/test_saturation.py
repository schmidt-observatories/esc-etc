"""Peak-pixel saturation model (issue #11)."""
import astropy.units as u
import pytest

pytest.importorskip("config_stp_esc")
pytest.importorskip("config_um")

from esc_etc import Simulation


def test_default_peak_fraction_matches_hand_airy_value():
    s = Simulation.from_default().sensor
    # 6.18 pix per lambda/D -> pixel area 0.0262 (lambda/D)^2; Airy peak pi/4
    # -> 0.0206 of the total; encircled energy inside r = 0.5 lambda/D is 0.456.
    assert s.peak_pixel_fraction == pytest.approx(0.0206 / 0.456, rel=0.02)
    # the peak pixel is brighter than the aperture mean
    assert s.peak_pixel_fraction * s.num_psf_pixels.value > 1


def test_saturation_time_uses_specified_fraction_headroom_and_dark():
    sim = Simulation.from_default()
    sim.update(sensor__peak_pixel_fraction=0.1, sensor__headroom=1.0)
    r, s = sim.count_rate_components(), sim.sensor
    per_pix = (0.1 * (r.source + r.speckle)
               + (r.zodi + r.exozodi) / s.num_psf_pixels.value).value + s.dark_current.value
    assert sim.saturation_time().to_value(u.s) == pytest.approx(s.well_depth.value / per_pix)
    sim.update(sensor__headroom=0.5)
    assert sim.saturation_time().to_value(u.s) == pytest.approx(0.5 * s.well_depth.value / per_pix)


def test_dark_current_shortens_saturation_time():
    sim = Simulation.from_default()
    t0 = sim.saturation_time()
    sim.update(sensor__dark_current=100 * sim.sensor.dark_current)
    assert sim.saturation_time() < t0
