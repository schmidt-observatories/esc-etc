import astropy.units as u
import numpy as np
import pytest

pytest.importorskip("config_um_esc")
pytest.importorskip("config_um")

from esc_etc.telescope import Telescope
from esc_etc.coronagraph import Coronagraph


def test_speckle_and_floor_scaling():
    t = Telescope.from_default()
    c = Coronagraph.from_default(t, raw_dh_contrast=1e-8, ppgain=10, separation=0.4)
    # speckle_scale == raw_dh_contrast (plan physics-fact #3)
    assert c.speckle_scale() == pytest.approx(1e-8, rel=1e-9)
    # noise-floor factor is 1/ppgain (plan physics-fact #4)
    assert c.noise_floor_factor() == pytest.approx(0.1, rel=1e-9)


def test_off_axis_throughput_in_unit_interval_and_separation_dependent():
    t = Telescope.from_default()
    c = Coronagraph.from_default(t, separation=0.4)
    k_near = c.off_axis_throughput(0.1)
    k_far = c.off_axis_throughput(0.4)
    assert 0.0 <= k_near <= 1.0
    assert 0.0 <= k_far <= 1.0
    # Throughput rises with separation away from the mask center.
    assert k_far >= k_near
