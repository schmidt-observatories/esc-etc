"""Regression tests for the six P0 correctness bugs in issue #27."""

import astropy.units as u
import pytest

from esc_etc import Simulation, Telescope, Sensor


@pytest.fixture(scope="module")
def sim():
    return Simulation.from_default()


# 1. SNR must not depend on the unit total_time / frame_time are given in.
def test_snr_independent_of_time_unit(sim):
    hours = sim.get_snr(1 * u.h, 100 * u.s)["snr"]
    seconds = sim.get_snr(3600 * u.s, 100 * u.s)["snr"]
    assert hours == pytest.approx(seconds)
    minutes = sim.get_snr(3600 * u.s, (100 / 60) * u.min)["snr"]
    assert minutes == pytest.approx(seconds)


def test_snr_accepts_plain_floats_as_seconds(sim):
    assert sim.get_snr(3600, 100)["snr"] == pytest.approx(
        sim.get_snr(3600 * u.s, 100 * u.s)["snr"]
    )
    assert (
        sim.get_int_time_for_snr(5, 100)["int_time"]
        == sim.get_int_time_for_snr(5, 100 * u.s)["int_time"]
    )


# 2. lifetime is validated, and never silently ignored.
def test_lifetime_is_validated():
    with pytest.raises(ValueError, match="lifetime"):
        Simulation.from_default(lifetime="nonsense")
    with pytest.raises(ValueError, match="lifetime"):
        Simulation.from_default(filter="F630N", lifetime="nonsense")


def test_lifetime_without_filter_is_rejected():
    # the generic config chain has no BOL/EOL variants; bol would be a no-op
    with pytest.raises(ValueError, match="lifetime"):
        Simulation.from_default(lifetime="bol")


# 3. Simulation.reset() restores nested components.
def test_simulation_reset_recurses_into_components():
    sim = Simulation.from_default()
    ppgain0 = sim.coronagraph.ppgain
    sim.update(coronagraph__ppgain=50, sensor__aperture="box")
    sim.reset()
    assert sim.coronagraph.ppgain == ppgain0
    assert sim.sensor.aperture == "resel"


# 4. Sensor.reset() returns to the auto peak-pixel model.
def test_sensor_reset_restores_auto_peak_pixel():
    sim = Simulation.from_default()
    auto = sim.sensor.peak_pixel_fraction
    sim.update(sensor__peak_pixel_fraction=0.5)
    assert sim.sensor.peak_pixel_fraction == 0.5
    sim.sensor.reset()
    assert sim.sensor.peak_pixel_fraction == pytest.approx(auto)
    assert sim.saturation_time().unit.is_equivalent(u.s)


def test_sensor_reset_after_aperture_change_keeps_saturation_working():
    sim = Simulation.from_default()
    sim.update(sensor__aperture="box")
    sim.sensor.reset()
    assert sim.saturation_time() > 0 * u.s
    assert sim.get_snr(3600 * u.s, 100 * u.s)["snr"] > 0


# 5. encircled_energy override must be a fraction in (0, 1].
@pytest.mark.parametrize("bad", [-0.5, 0.0, 1.7])
def test_encircled_energy_out_of_range_is_rejected(bad):
    sim = Simulation.from_default()
    before = sim.sensor.ee_fraction
    with pytest.raises(ValueError, match="encircled_energy"):
        sim.update(sensor__encircled_energy=bad)
    assert sim.sensor.ee_fraction == before  # rejected update leaves no trace


def test_encircled_energy_in_range_is_accepted():
    sim = Simulation.from_default()
    sim.update(sensor__encircled_energy=1.0)
    assert sim.sensor.ee_fraction == 1.0


# 6. Component API: the sensor bandpass and the telescope geometry must agree.
def test_component_api_rejects_filter_geometry_mismatch():
    t = Telescope.from_default()  # 630 nm config default
    with pytest.raises(ValueError, match="filter"):
        Sensor.from_default(t, filter="B1")  # 400 nm bandpass
    with pytest.raises(ValueError, match="filter"):
        Sensor.from_default(Telescope.from_default(filter="B1"))  # generic 630 nm chain


def test_component_api_matches_simulation_path():
    t = Telescope.from_default(filter="B1")
    s = Sensor.from_default(t, filter="B1")
    ref = Simulation.from_default(filter="B1").sensor
    assert s.num_psf_pixels == ref.num_psf_pixels
    assert s.peak_pixel_fraction == pytest.approx(ref.peak_pixel_fraction)


@pytest.mark.parametrize(
    "key, unit",
    [
        ("read_noise", u.electron**0.5 / u.pix**0.5),
        ("dark_current", u.electron / (u.s * u.pix)),
        ("well_depth", u.electron / u.pix),
    ],
)
def test_update_sensor_quantities_accept_plain_numbers(key, unit):
    # The docs show sim.update(sensor__read_noise=5); a bare number must behave
    # like the same value in the sensor's own unit, not break the next get_snr.
    sim = Simulation.from_default()
    sim.update(**{f"sensor__{key}": 5})
    plain = sim.get_snr(3600, 100)["snr"], sim.saturation_time()
    sim.update(**{f"sensor__{key}": 5 * unit})
    assert plain == (sim.get_snr(3600, 100)["snr"], sim.saturation_time())
