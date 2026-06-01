import pytest

pytest.importorskip("config_stp_esc")
pytest.importorskip("config_um")

from physics_helpers import esc_snr, BASELINE


def test_baseline_runs_and_is_finite():
    snr, esc = esc_snr()
    assert snr > 0 and snr == snr  # finite, positive (NaN != NaN)
    assert esc.source_counts.value > 0
