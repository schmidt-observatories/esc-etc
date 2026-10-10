"""Magnitude/flux scaling laws and monotonicity.

Measured 2026-06-01: source_counts follows 10^(-0.4*mag) exactly
(dmag 18/20/22 -> 5.778 / 0.9158 / 0.1451, each 2-mag step = x6.31).

NOTE: the originally-planned collecting-area D^2 test is intentionally absent.
The Observatory(name, diameter, focal_len) constructor args are overridden by
the telescope config in make_STP(), so aperture is not a free knob through the
public API. The host-magnitude flux law below exercises the same
F0*10^(-0.4*mag)*area*throughput physics via a knob the API controls.
"""
import pytest


from physics_helpers import esc_snr


def test_planet_counts_follow_delta_magnitude_law():
    # A 2.5-mag fainter planet => 10x fewer planet counts.
    _, esc_bright = esc_snr(planetdeltamag=20.0)
    _, esc_faint = esc_snr(planetdeltamag=22.5)
    ratio = esc_bright.source_counts.value / esc_faint.source_counts.value
    assert ratio == pytest.approx(10.0, rel=1e-2)


def test_five_magnitudes_is_factor_100():
    _, esc_bright = esc_snr(planetdeltamag=18.0)
    _, esc_faint = esc_snr(planetdeltamag=23.0)
    ratio = esc_bright.source_counts.value / esc_faint.source_counts.value
    assert ratio == pytest.approx(100.0, rel=1e-2)


def test_fainter_planet_lowers_snr_monotonically():
    dmags = [18.0, 19.0, 20.0, 21.0, 22.0]
    snrs = [esc_snr(planetdeltamag=d)[0] for d in dmags]
    for hi, lo in zip(snrs, snrs[1:]):
        assert lo < hi  # strictly decreasing as planet gets fainter


def test_host_magnitude_flux_law():
    # At fixed planetdeltamag, planet counts scale with host flux:
    # 2.5-mag brighter host => 10x source_counts.
    _, esc_dim = esc_snr(hoststarmag=-0.353)
    _, esc_bright = esc_snr(hoststarmag=-2.853)
    ratio = esc_bright.source_counts.value / esc_dim.source_counts.value
    assert ratio == pytest.approx(10.0, rel=2e-2)


def test_brighter_host_raises_snr():
    snr_dim, _ = esc_snr(hoststarmag=-0.353)
    snr_bright, _ = esc_snr(hoststarmag=-1.0)
    assert snr_bright > snr_dim
