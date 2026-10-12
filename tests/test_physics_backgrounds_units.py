"""Background scaling, unit/sanity checks, and saturation-time behavior.

Backgrounds are surface brightnesses in mag/arcsec^2: a *smaller* bg_flux /
exobg_flux number is *brighter* and yields more sky/exozodi counts.
"""

import astropy.units as u


from physics_helpers import esc_snr


def test_brighter_zodi_raises_sky_counts():
    _, esc_dark = esc_snr(bg_flux=22.5)
    _, esc_bright = esc_snr(bg_flux=20.0)
    assert esc_bright.sky_counts.value > esc_dark.sky_counts.value


def test_brighter_zodi_does_not_raise_snr():
    snr_dark, _ = esc_snr(bg_flux=22.5)
    snr_bright, _ = esc_snr(bg_flux=20.0)
    # More background can only hurt (or leave unchanged) the SNR.
    assert snr_bright <= snr_dark + 1e-9


def test_brighter_exozodi_raises_exozodi_counts():
    _, esc_dark = esc_snr(exobg_flux=21.0)
    _, esc_bright = esc_snr(exobg_flux=18.0)
    assert esc_bright.exozodi_counts.value > esc_dark.exozodi_counts.value


def test_count_rates_carry_expected_units_and_are_nonnegative():
    _, esc = esc_snr()
    for attr in ("source_counts", "sky_counts", "speckle_counts", "exozodi_counts"):
        q = getattr(esc, attr)
        assert q.unit.is_equivalent(u.electron / u.s), f"{attr} wrong unit: {q.unit}"
        assert q.value >= 0.0, f"{attr} negative: {q.value}"
    assert esc.num_psf_pixels.unit.is_equivalent(u.pix)
    assert esc.num_psf_pixels.value > 0


def test_snr_is_finite_and_positive():
    snr, _ = esc_snr()
    assert snr > 0 and snr == snr


def test_saturation_time_drops_as_source_brightens():
    _, esc_dim = esc_snr(hoststarmag=-0.353)
    _, esc_bright = esc_snr(hoststarmag=-2.0)
    t_dim = esc_dim.calc_saturation_time().value
    t_bright = esc_bright.calc_saturation_time().value
    assert t_bright < t_dim
