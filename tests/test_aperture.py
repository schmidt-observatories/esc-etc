"""One extraction aperture for every SNR term (issue #10)."""
import astropy.units as u
import pytest


from esc_etc import Coronagraph, Sensor, Simulation, Telescope, get_scene


def test_detector_pixels_and_background_solid_angle_agree():
    sim = Simulation.from_default()
    omega_pix = sim.sensor.num_psf_pixels.value * sim.sensor.plate_scale ** 2
    assert omega_pix == pytest.approx(sim.telescope.resel.to_value(u.arcsec ** 2))


def test_point_source_rates_trace_to_definitions():
    sim = Simulation.from_default(planetdeltamag=20.0, contrast=1e-8, separation=0.4)
    r = sim.count_rate_components()
    k = sim.coronagraph.off_axis_throughput()
    ee = sim.sensor.ee_fraction            # Airy light inside the resel, 0.456
    host_raw = r.host / k
    assert r.source.value == pytest.approx((host_raw * 10 ** (-0.4 * 20.0) * k * ee).value)
    assert r.speckle.value == pytest.approx((host_raw * 1e-8 * k * ee).value)


def test_doubling_aperture_doubles_diffuse_and_detector_terms_and_grows_encircled_energy():
    t = Telescope.from_default()
    base = Simulation(t, Sensor.from_default(t), get_scene(t), Coronagraph.from_default(t))
    t2 = Telescope.from_default()
    t2.resel = 2 * t.resel
    wide = Simulation(t2, Sensor.from_default(t2), get_scene(t2), Coronagraph.from_default(t2))
    rb, rw = base.count_rate_components(), wide.count_rate_components()
    assert wide.sensor.num_psf_pixels.value == pytest.approx(2 * base.sensor.num_psf_pixels.value)
    assert rw.zodi.value == pytest.approx(2 * rb.zodi.value)
    assert rw.exozodi.value == pytest.approx(2 * rb.exozodi.value)
    # point sources gain only the extra encircled energy of the wider disk
    ee_ratio = wide.sensor.ee_fraction / base.sensor.ee_fraction
    assert 1 < ee_ratio < 2
    assert rw.source.value == pytest.approx(rb.source.value * ee_ratio)
    assert rw.speckle.value == pytest.approx(rb.speckle.value * ee_ratio)
