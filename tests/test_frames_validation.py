"""Integer frame accounting and input validation (issue #15)."""
import astropy.units as u
import numpy as np
import pytest

pytest.importorskip("config_stp_esc")
pytest.importorskip("config_um")

from esc_etc import Coronagraph, Simulation, Telescope


@pytest.fixture(scope="module")
def sim():
    return Simulation.from_default()


def test_reads_are_integer_and_at_least_one(sim):
    # 10 s of 100 s frames is one read, same as 10 s of 10 s frames.
    one_a = sim.get_snr(10 * u.s, 100 * u.s)["snr"]
    one_b = sim.get_snr(10 * u.s, 10 * u.s)["snr"]
    assert one_a == pytest.approx(one_b)
    # 150 s of 100 s frames is two reads (one full + one short), same as 2 x 75 s.
    assert sim.get_snr(150 * u.s, 100 * u.s)["snr"] == pytest.approx(
        sim.get_snr(150 * u.s, 75 * u.s)["snr"])
    # more reads -> more read noise -> lower SNR
    assert sim.get_snr(150 * u.s, 100 * u.s)["snr"] < sim.get_snr(150 * u.s, 150 * u.s)["snr"]


def test_int_time_is_whole_frames_and_meets_target(sim):
    out = sim.get_int_time_for_snr(7.0, frame_time=100 * u.s)
    t = out["int_time"][0]
    assert (t / (100 * u.s)).value == pytest.approx(round((t / (100 * u.s)).value))
    assert t >= out["int_time_continuous"][0]
    assert sim.get_snr(t, 100 * u.s)["snr"] >= 7.0 - 1e-9


@pytest.mark.parametrize("kw", [dict(total_time=0 * u.s, frame_time=100 * u.s),
                                dict(total_time=100 * u.s, frame_time=-1 * u.s)])
def test_nonpositive_times_raise(sim, kw):
    with pytest.raises(ValueError):
        sim.get_snr(**kw)


def test_nonpositive_snr_raises(sim):
    with pytest.raises(ValueError):
        sim.get_int_time_for_snr(0.0, frame_time=100 * u.s)


def test_coronagraph_domain_validation():
    t = Telescope.from_default()
    with pytest.raises(ValueError):
        Coronagraph.from_default(t, ppgain=0)
    with pytest.raises(ValueError):
        Coronagraph.from_default(t, raw_dh_contrast=-1e-9)
    c = Coronagraph.from_default(t)
    with pytest.raises(ValueError):
        c.update(ppgain=-1)
    c.update(raw_dh_contrast=0.0)  # zero speckle is a valid limit
    with pytest.raises(ValueError, match="outside"):
        c.off_axis_throughput(5.0)


def test_saturated_frame_time_warns(sim):
    t_sat = sim.saturation_time()
    with pytest.warns(UserWarning, match="saturat"):
        sim.get_snr(4 * t_sat, 2 * t_sat)
