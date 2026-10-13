"""End-of-life ESC filter curves shipped in esc_etc/data/esc_filters_eol (Lazuli throughput
budget chain incl. QE, EOL contamination and reserves; vortex and Lyot factors
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


def test_filter_headers_cite_the_budget_by_date_only():
    """The shipped curves name the Lazuli budget and its date, not the internal
    budget document, review milestone or margin numbers (issue #29)."""
    from esc_etc.sensor import _DATA

    files = [
        f
        for life in ("eol", "bol")
        for f in sorted(_DATA.glob(f"esc_filters_{life}/ESC_*.csv"))
    ]
    assert len(files) == 24
    for f in files:
        header = f.open().readline()
        assert header.startswith("# ESC ")
        assert "Lazuli throughput budget, 2026-03-25" in header
        for word in ("Pearl", "PLSE", "MPDR", "v0.4", "%", "0.446", "0.81"):
            assert word not in header.split(":", 1)[1], (f.name, word)
