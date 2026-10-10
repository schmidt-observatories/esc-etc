"""Coronagraphic knobs: contrast, post-processing gain, and separation.

Measured 2026-06-01: speckle_counts is linear in contrast (1e-9/1e-8/1e-7 ->
0.0916/0.9158/9.158); noise floor M = speckle_counts * (1/ppgain_input), and
esc.ppgain == 1/ppgain_input (input 10 -> 0.1).
"""
import pytest


from physics_helpers import esc_snr


def test_deeper_contrast_raises_snr():
    snr_shallow, _ = esc_snr(contrast=1e-7)
    snr_base, _ = esc_snr(contrast=1e-8)
    snr_deep, _ = esc_snr(contrast=1e-9)
    assert snr_deep > snr_base > snr_shallow


def test_speckle_counts_linear_in_contrast():
    _, esc_a = esc_snr(contrast=1e-8)
    _, esc_b = esc_snr(contrast=1e-9)
    # 10x deeper contrast => 10x fewer speckle counts.
    ratio = esc_a.speckle_counts.value / esc_b.speckle_counts.value
    assert ratio == pytest.approx(10.0, rel=1e-3)


def test_ppgain_sets_noise_floor():
    _, esc = esc_snr(ppgain=10.0)
    # Internal ppgain is the post-processing factor = 1 / input.
    assert esc.ppgain == pytest.approx(0.1, rel=1e-6)


def test_higher_ppgain_raises_snr():
    snr_low, _ = esc_snr(ppgain=1.0)
    snr_high, _ = esc_snr(ppgain=100.0)
    assert snr_high > snr_low


def test_separation_changes_snr_and_stays_finite():
    # Throughput depends on off-axis separation via the vvc lambda/D mask curve.
    seps = [0.2, 0.3, 0.4, 0.6]
    snrs = [esc_snr(separation=s)[0] for s in seps]
    for snr in snrs:
        assert snr > 0 and snr == snr  # positive, finite
    # The mask makes throughput (hence SNR) genuinely separation-dependent.
    assert max(snrs) > min(snrs) * (1 + 1e-3)
