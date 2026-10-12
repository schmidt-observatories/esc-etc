"""The planet spectrum is used in the count-rate chain (issue #13)."""
import astropy.units as u
import pytest
from synphot import SourceSpectrum
from synphot.models import BlackBody1D


from esc_etc import Simulation

RED = SourceSpectrum(BlackBody1D, temperature=1000 * u.K)


def test_default_is_host_scaled_by_deltamag():
    sim = Simulation.from_default(planetdeltamag=20.0)
    r = sim.count_rate_components()
    # host is the k-scaled full-PSF rate; the planet is also credited only the
    # encircled energy inside the noise aperture
    assert r.source.value == pytest.approx((r.host * 10 ** (-0.4 * 20.0) * sim.sensor.ee_fraction).value, rel=1e-6)


def test_esc_band_reference_is_shape_independent():
    sim = Simulation.from_default()
    flat = sim.count_rate_components().source
    sim.update(scene__planet__spectrum=RED)
    # deltamag defined in the observing band pins the ESC count rate regardless of colour
    assert sim.count_rate_components().source.value == pytest.approx(flat.value, rel=1e-6)


def test_v_band_reference_makes_planet_colour_matter():
    sim = Simulation.from_default()
    sim.update(scene__planet__deltamag_band="johnson_v")
    flat_v = sim.count_rate_components().source
    sim.update(scene__planet__spectrum=RED)
    red_v = sim.count_rate_components().source
    # a 1000 K planet is far redder than flat between V (550 nm) and the ESC band (633 nm)
    assert red_v.value > 3 * flat_v.value
