# tests/test_telescope.py
import astropy.units as u
import pytest

pytest.importorskip("config_stp_esc")
pytest.importorskip("config_um")

from esc_etc.telescope import Telescope


def test_from_default_geometry():
    t = Telescope.from_default()
    assert t.diameter_primary.unit.is_equivalent(u.m)
    assert t.surface.unit.is_equivalent(u.m ** 2)
    # Lyot collecting area is strictly smaller than the geometric primary area.
    geom = 3.14159265 * (0.5 * t.diameter_primary) ** 2
    assert t.surface < geom
    assert t.primary_filter.unit.is_equivalent(u.AA)
    assert t.resel.unit.is_equivalent(u.arcsec ** 2)
    assert float(t.f_num) > 0
