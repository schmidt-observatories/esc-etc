"""End-of-life ESC filter curves shipped in esc_etc/data/esc_filters_eol (Pearl PLSE
budget v0.4 chain incl. QE, EOL contamination and reserves; vortex and Lyot factors
excluded because Coronagraph and Telescope.surface apply them)."""

import astropy.units as u
import pytest


from esc_etc import FILTERS, Sensor, Simulation, Telescope


def test_twelve_filters_by_slot_and_designation():
    assert len(set(FILTERS.values())) == 12
    assert FILTERS["R1"] == FILTERS["F620N"]
    assert FILTERS["R5"] == FILTERS["F725.9N"]


def test_filter_sets_central_wavelength():
    assert Telescope.from_default(filter="R1").primary_filter.to_value(
        u.nm
    ) == pytest.approx(620)
    assert Telescope.from_default(filter="R5").primary_filter.to_value(
        u.nm
    ) == pytest.approx(725.9)
    # resel follows lambda
    assert (
        Telescope.from_default(filter="R1").resel
        > Telescope.from_default(filter="B1").resel
    )


def test_filter_bandpass_is_the_csv_curve():
    t = Telescope.from_default(filter="R1")
    s = Sensor.from_default(t, filter="R1")
    assert float(s.bandpass(620 * u.nm)) == pytest.approx(0.08834, rel=1e-6)
    assert float(s.bandpass(700 * u.nm)) == pytest.approx(0.0, abs=1e-6)


def test_unknown_filter_raises():
    with pytest.raises(ValueError, match="F999N"):
        Telescope.from_default(filter="F999N")
    with pytest.raises(ValueError, match="F999N"):
        Sensor.from_default(Telescope.from_default(), filter="F999N")


def test_simulation_filter_changes_rates():
    default = Simulation.from_default().count_rate_components().host.value
    r1 = Simulation.from_default(filter="R1").count_rate_components().host.value
    b1 = Simulation.from_default(filter="B1").count_rate_components().host.value
    assert r1 != pytest.approx(default, rel=1e-3)
    assert b1 < r1
