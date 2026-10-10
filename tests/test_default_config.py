"""The default configuration is the UA Ultramarine 3 m telescope with the
config_um_esc ESC instrument (issue: esc_etc defaulted to the 2.43 m config_um_esc)."""
import copy

import astropy.units as u
import pytest


from esc_etc import Sensor, Simulation, Telescope, uasal_config


def test_default_telescope_is_3m():
    assert Telescope.from_default().diameter_primary.to_value(u.m) == pytest.approx(3.0)


def test_default_sensor_builds_at_nominal_temperature():
    # config_um_esc says -20 C, just below the dark-current table's first row;
    # the table value is clamped instead of raising.
    s = Sensor.from_default(Telescope.from_default())
    assert s.sensor_temp.value == -20
    assert 0 < s.dark_current.value < 0.01


def test_dichroic_throughput_is_applied():
    t = Telescope.from_default()
    cfg = copy.deepcopy(uasal_config.load_config_values("config_um_esc"))
    cfg["common_params"]["arm_a"]["optics"]["dichroic"]["dichroic_throughput"] = 0.5
    half = Sensor.from_config(cfg, uasal_config.get_data_path("config_um_esc"),
                              uasal_config.load_config_values("config_um"),
                              uasal_config.get_data_path("config_um"), t)
    full = Sensor.from_default(t)
    assert float(half.bandpass(630 * u.nm)) == pytest.approx(0.5 / 0.9 * float(full.bandpass(630 * u.nm)), rel=1e-6)


def test_default_simulation_geometry():
    sim = Simulation.from_default()
    assert sim.sensor.num_psf_pixels.value == pytest.approx(19.595, rel=1e-3)
    assert sim.telescope.primary_filter.to_value(u.nm) == pytest.approx(630.0)
