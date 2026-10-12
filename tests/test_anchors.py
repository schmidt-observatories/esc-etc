"""Pinned golden anchors. These catch uniform regressions that scaling-law
tests (ratios/directions) would miss. Values measured 2026-06-01 against the
editable esc_etc install, re-pinned 2026-09-12 for the single-aperture model
(issue #10) and 2026-09-13 for the config_um_esc 3 m default (source rate x5.9 =
area 1.56 x throughput 3.52 x FPM 1.07), then again 2026-09-13 for the
encircled-energy default (point-source rates x0.456, Airy EE in the resel). If one changes, investigate before editing it.
"""

import astropy.units as u
import pytest


import esc_etc.ExposureTimeSNRCalculatorESC as esc_mod
from physics_helpers import esc_snr


def test_anchor_baseline_snr():
    # esc_calc_snr(3600, 100, separation=0.4, contrast=1e-8, ppgain=10)
    snr, _ = esc_snr()
    assert snr == pytest.approx(9.87424, rel=2e-3)


def test_anchor_default_call_600_10():
    # Default separation=0.2 path (the historical test_snr.py configuration).
    snr, esc = esc_mod.esc_calc_snr(600, 10, verbose=False, plot=False)
    assert float(snr) == pytest.approx(8.11414, rel=1e-3)


def test_anchor_baseline_counts():
    _, esc = esc_snr()
    assert esc.source_counts.value == pytest.approx(2.479242, rel=1e-3)
    assert esc.sky_counts.value == pytest.approx(8.646151e-04, rel=1e-3)
    # speckle == source at contrast 1e-8 / dmag 20 for this config
    assert esc.speckle_counts.value == pytest.approx(2.479242, rel=1e-3)
    assert esc.num_psf_pixels.value == pytest.approx(19.5951, rel=1e-4)
