# tests/test_sensor.py
import astropy.units as u
import pytest

pytest.importorskip("config_stp_esc")
pytest.importorskip("config_um")

from esc_etc.telescope import Telescope
from esc_etc.sensor import Sensor


def test_from_default_detector_and_psf():
    t = Telescope.from_default()
    s = Sensor.from_default(t)
    assert s.gain.unit.is_equivalent(u.electron / u.ct)
    assert s.dark_current.unit.is_equivalent(u.electron / (u.s * u.pix))
    assert s.well_depth.unit.is_equivalent(u.electron / u.pix)
    # Square-approx PSF footprint pinned by the baseline config.
    assert s.num_psf_pixels.value == pytest.approx(225.0)
    # Bandpass is a synphot SpectralElement evaluable on the detector grid.
    assert float(s.bandpass.tpeak()) > 0
