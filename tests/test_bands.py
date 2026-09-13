"""Explicit reference bands and magnitude systems (issue #14)."""
import astropy.units as u
import pytest
from synphot import Observation, SourceSpectrum, SpectralElement, units as su
from synphot.models import BlackBody1D

pytest.importorskip("config_um_esc")
pytest.importorskip("config_um")

import esc_etc.ExposureTimeSNRCalculatorESC as shim
from esc_etc import SceneElement, Simulation

RED = SourceSpectrum(BlackBody1D, temperature=3000 * u.K)


def test_catalog_v_host_is_normalized_in_johnson_v():
    sim = Simulation.from_default(hoststarmag=5.0, hoststar_band="johnson_v")
    sim.update(scene__star__spectrum=RED)
    host_sp = sim._normalize(sim.scene.star, 5.0, "johnson_v")
    v = Observation(host_sp, SpectralElement.from_filter("johnson_v")).effstim(
        su.VEGAMAG, vegaspec=SourceSpectrum.from_vega())
    assert v.value == pytest.approx(5.0, abs=1e-6)
    # and the ESC-band interpretation of the same number gives a different rate
    esc = Simulation.from_default(hoststarmag=5.0)
    esc.update(scene__star__spectrum=RED)
    assert sim.count_rate_components().host.value != pytest.approx(
        esc.count_rate_components().host.value, rel=1e-3)


def test_vega_and_ab_differ_and_invalid_fails_loudly():
    vega, _ = shim.esc_calc_snr(3600, 100, flux_units="vega", verbose=False)
    ab, _ = shim.esc_calc_snr(3600, 100, flux_units="AB", verbose=False)
    assert vega != pytest.approx(ab, rel=1e-3)
    with pytest.raises(ValueError, match="mag_system"):
        shim.esc_calc_snr(3600, 100, flux_units="jansky", verbose=False)
    with pytest.raises(ValueError):
        SceneElement("x", RED, mag=0.0, mag_system="foo")


def test_default_bands_are_explicit():
    scene = Simulation.from_default().scene
    assert scene.star.band is None            # ESC band
    assert scene.zodi.band == "johnson_v"
    assert scene.exozodi.band is None         # ESC band, host + exobg_flux
