"""Switchable throughput lifetime (EOL / BOL curve sets) and switchable noise
aperture with its encircled-energy fraction."""

import numpy as np
import astropy.units as u
import pytest


from esc_etc import Sensor, Simulation, Telescope


# ------------------------------------------------------------------ lifetime
def test_lifetime_selects_curve_set():
    t = Telescope.from_default(filter="F630N")
    eol = Sensor.from_default(t, filter="F630N")  # default lifetime
    bol = Sensor.from_default(t, filter="F630N", lifetime="bol")
    assert float(eol.bandpass(630 * u.nm)) == pytest.approx(0.0916449, rel=1e-6)
    assert float(bol.bandpass(630 * u.nm)) == pytest.approx(0.11991, rel=1e-6)
    with pytest.raises(ValueError, match="lifetime"):
        Sensor.from_default(t, filter="F630N", lifetime="mid")


def test_simulation_lifetime_changes_rates():
    eol = Simulation.from_default(filter="F630N").count_rate_components().host.value
    bol = (
        Simulation.from_default(filter="F630N", lifetime="bol")
        .count_rate_components()
        .host.value
    )
    assert bol / eol == pytest.approx(0.11991 / 0.0916449, rel=1e-2)


# ------------------------------------------------------------------ aperture
def test_default_aperture_is_resel_with_airy_encircled_energy():
    s = Simulation.from_default().sensor
    assert s.aperture == "resel"
    assert s.num_psf_pixels.value == pytest.approx(19.595, rel=1e-3)
    assert s.ee_fraction == pytest.approx(0.456, abs=0.005)
    assert s.aperture_solid_angle.to_value(u.arcsec**2) == pytest.approx(
        s.num_psf_pixels.value * s.plate_scale**2
    )


def test_aperture_choices_pixels_and_encircled_energy():
    sim = Simulation.from_default()
    sim.update(sensor__aperture="optimal")
    assert sim.sensor.num_psf_pixels.value == pytest.approx(
        np.pi * (0.7 * 4.995) ** 2, rel=1e-2
    )
    assert sim.sensor.ee_fraction == pytest.approx(0.678, abs=0.005)
    sim.update(sensor__aperture="box")  # UA: n x n, n = ceil(2.44 lambda F# / pixel)
    assert sim.sensor.num_psf_pixels.value == 169
    assert sim.sensor.ee_fraction == pytest.approx(0.85, abs=0.01)
    sim.update(sensor__aperture="matched")  # N_eff = 1 / sum p_i^2, EE = 1
    assert sim.sensor.num_psf_pixels.value == pytest.approx(70.5, rel=0.02)
    assert sim.sensor.ee_fraction == 1.0
    with pytest.raises(ValueError, match="aperture"):
        sim.update(sensor__aperture="hexagon")


def test_encircled_energy_scales_point_sources_and_area_scales_diffuse():
    sim = Simulation.from_default()
    r_ee = sim.count_rate_components()
    sim.update(sensor__encircled_energy=1.0)
    r_full = sim.count_rate_components()
    assert r_ee.source.value / r_full.source.value == pytest.approx(0.456, abs=0.005)
    assert r_ee.speckle.value / r_full.speckle.value == pytest.approx(0.456, abs=0.005)
    assert r_ee.zodi.value == pytest.approx(r_full.zodi.value)
    sim.update(sensor__aperture="box")  # encircled_energy override still 1.0
    r_box = sim.count_rate_components()
    assert r_box.source.value == pytest.approx(r_full.source.value)
    assert r_box.zodi.value / r_full.zodi.value == pytest.approx(169 / 19.595, rel=1e-3)


def test_box_with_full_flux_reproduces_upstream_convention():
    # As-coded upstream: 169 detector pixels, planet credited with all its flux.
    sim = Simulation.from_default()
    sim.update(sensor__aperture="box", sensor__encircled_energy=1.0)
    t = sim.get_int_time_for_snr(5, 60 * u.s)["int_time_continuous"]
    sim2 = Simulation.from_default()
    sim2.update(sensor__encircled_energy=1.0)
    sim2.sensor.num_psf_pixels = (
        169 * u.pix
    )  # the manual override used in the Atlas cross-check
    sim2.sensor.aperture_solid_angle = 169 * sim2.sensor.plate_scale**2 * u.arcsec**2
    t2 = sim2.get_int_time_for_snr(5, 60 * u.s)["int_time_continuous"]
    assert t.value == pytest.approx(t2.value, rel=1e-6)
