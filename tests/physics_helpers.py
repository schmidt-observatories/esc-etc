"""Shared helpers for the ESC ETC physics test suite.

`esc_snr` wraps `esc_calc_snr` with a single canonical baseline so individual
tests only specify what they vary. Results are memoized on the override set so
repeated configurations across tests don't pay the ~0.4 s ETC cost twice.
"""
import functools
import types

import esc_etc.ExposureTimeSNRCalculatorESC as esc_mod

# Canonical baseline observation. SNR for these settings is ~8.9221 (see
# test_anchors.py). `verbose`/`plot` are off so the suite stays quiet/headless.
_BASELINE = dict(
    exp_time=3600.0,
    int_time=100.0,
    hoststarmag=-0.353,
    contrast=1e-8,
    planetdeltamag=20.0,
    bg_flux=22.5,
    exobg_flux=21.0,
    flux_units="vega",
    separation=0.4,
    ppgain=10.0,
    verbose=False,
    plot=False,
)
BASELINE = types.MappingProxyType(_BASELINE)


@functools.lru_cache(maxsize=None)
def _cached(items):
    kwargs = dict(BASELINE)
    kwargs.update(dict(items))
    return esc_mod.esc_calc_snr(**kwargs)


def esc_snr(**overrides):
    """Run `esc_calc_snr` from BASELINE with `overrides`.

    Returns ``(snr, esc)`` where ``snr`` is a float and ``esc`` is the
    configured Observatory (carrying ``source_counts``, ``sky_counts``,
    ``speckle_counts``, ``exozodi_counts``, ``ppgain``, etc.).

    The returned Observatory is shared/memoized — treat it as read-only; do not mutate its attributes.
    """
    snr, observatory = _cached(tuple(sorted(overrides.items())))
    return float(snr), observatory
