# ESC ETC Physics Test Suite — Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Add a physics-based pytest suite for the ESC ETC (`esc_etc`) that asserts scaling laws/invariants plus a few pinned anchors, and migrate the existing `stp_etc_esc`-based tests onto `esc_etc`.

**Architecture:** Themed test files under `tests/`, sharing one helper module (`physics_helpers.py`) that wraps `esc_calc_snr` with a canonical baseline + `lru_cache` memo. Invariant tests use directional/ratio assertions with generous tolerances; an isolated `test_anchors.py` pins measured golden values.

**Tech Stack:** Python, pytest, astropy units, numpy, matplotlib (Agg, headless). `esc_etc` editable-installed so imports resolve to repo source.

---

## Important notes for the implementer

- **`esc_calc_snr` returns a `(snr, esc)` tuple.** Always unpack. `snr` is a Python/np float; `esc` is the configured `Observatory`.
- **The ETC is heavyweight (~0.4 s/call)** but the helper memoizes identical configs. The whole suite should run in < ~30 s.
- **All numbers below were measured on 2026-06-01** against the editable `esc_etc`. If a run differs, that is a real finding — investigate with superpowers:systematic-debugging before "fixing" the number.
- **These tests characterize already-working behavior**, so each test should **PASS on first correct run**. There is no "watch it fail" step (no new production code). An unexpected failure means a real bug in the ETC or the test.
- **Config repos required.** Each test module starts with `pytest.importorskip(...)` for `config_stp_esc` and `config_um` so the suite skips cleanly if configs are absent.
- **Do not** run a non-editable `pip install .` of `esc_etc` during this work — it re-shadows the editable install with a stale copy (the original `separation` bug).
- Run commands from the repo root: `/Users/gudmundurstefansson/Dropbox/mypylib/notebooks/GIT/lazuli_etc/esc-etc`.
- Work happens on branch `add-physics-tests` (already created).

## File structure

| File | Responsibility |
|---|---|
| `tests/conftest.py` (new) | Force headless matplotlib (`Agg`) for all tests |
| `tests/physics_helpers.py` (new) | `BASELINE` dict, memoized `esc_snr(**overrides) -> (snr, esc)` |
| `tests/test_anchors.py` (new) | Pinned golden SNR/counts values |
| `tests/test_physics_snr_time.py` (new) | SNR vs exp_time, sqrt(t), noise-floor ceiling |
| `tests/test_physics_scaling.py` (new) | Magnitude/flux laws, planet & host monotonicity |
| `tests/test_physics_coronagraph.py` (new) | contrast, ppgain, separation |
| `tests/test_physics_backgrounds_units.py` (new) | zodi/exozodi, units/sanity, saturation time |
| `tests/test_snr.py` (modify) | Repoint `stp_etc_esc` → `esc_etc`, unpack tuple |
| `tests/test_esc_etc_initialization.py` (modify) | Repoint `stp_etc_esc` → `esc_etc`, refresh goldens |

---

### Task 1: Test foundation (conftest + helper + smoke test)

**Files:**
- Create: `tests/conftest.py`
- Create: `tests/physics_helpers.py`
- Test: `tests/test_physics_smoke.py` (temporary, removed in Task 9 step)

- [ ] **Step 1: Create `tests/conftest.py`**

```python
# Headless matplotlib for the whole test session: the ETC's plot paths must
# never try to open a display under pytest/CI.
import matplotlib
matplotlib.use("Agg")
```

- [ ] **Step 2: Create `tests/physics_helpers.py`**

```python
"""Shared helpers for the ESC ETC physics test suite.

`esc_snr` wraps `esc_calc_snr` with a single canonical baseline so individual
tests only specify what they vary. Results are memoized on the override set so
repeated configurations across tests don't pay the ~0.4 s ETC cost twice.
"""
import functools

import esc_etc.ExposureTimeSNRCalculatorESC as esc_mod

# Canonical baseline observation. SNR for these settings is ~8.9221 (see
# test_anchors.py). `verbose`/`plot` are off so the suite stays quiet/headless.
BASELINE = dict(
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
    """
    snr, observatory = _cached(tuple(sorted(overrides.items())))
    return float(snr), observatory
```

- [ ] **Step 3: Create temporary smoke test `tests/test_physics_smoke.py`**

```python
import pytest

pytest.importorskip("config_stp_esc")
pytest.importorskip("config_um")

from physics_helpers import esc_snr, BASELINE


def test_baseline_runs_and_is_finite():
    snr, esc = esc_snr()
    assert snr > 0 and snr == snr  # finite, positive (NaN != NaN)
    assert esc.source_counts.value > 0
```

- [ ] **Step 4: Run the smoke test**

Run: `python -m pytest tests/test_physics_smoke.py -q`
Expected: `1 passed`. (Confirms helper import path + config availability.)

- [ ] **Step 5: Commit**

```bash
git add tests/conftest.py tests/physics_helpers.py tests/test_physics_smoke.py
git commit -m "test: add physics-test foundation (conftest + helper + smoke)"
```

---

### Task 2: Anchor tests (pinned golden values)

**Files:**
- Create: `tests/test_anchors.py`

- [ ] **Step 1: Create `tests/test_anchors.py`**

```python
"""Pinned golden anchors. These catch uniform regressions that scaling-law
tests (ratios/directions) would miss. Values measured 2026-06-01 against the
editable esc_etc install. If one changes, investigate before editing it.
"""
import astropy.units as u
import pytest

pytest.importorskip("config_stp_esc")
pytest.importorskip("config_um")

import esc_etc.ExposureTimeSNRCalculatorESC as esc_mod
from physics_helpers import esc_snr


def test_anchor_baseline_snr():
    # esc_calc_snr(3600, 100, separation=0.4, contrast=1e-8, ppgain=10)
    snr, _ = esc_snr()
    assert snr == pytest.approx(8.9221, rel=2e-3)


def test_anchor_default_call_600_10():
    # Default separation=0.2 path (the historical test_snr.py configuration).
    snr, esc = esc_mod.esc_calc_snr(600, 10, verbose=False, plot=False)
    assert float(snr) == pytest.approx(1.90435, rel=1e-3)


def test_anchor_baseline_counts():
    _, esc = esc_snr()
    assert esc.source_counts.value == pytest.approx(0.915824, rel=1e-3)
    assert esc.sky_counts.value == pytest.approx(2.276078e-4, rel=1e-3)
    # speckle == source at contrast 1e-8 / dmag 20 for this config
    assert esc.speckle_counts.value == pytest.approx(0.915824, rel=1e-3)
    assert esc.num_psf_pixels.value == pytest.approx(225.0)
```

- [ ] **Step 2: Run**

Run: `python -m pytest tests/test_anchors.py -q`
Expected: `3 passed`.

- [ ] **Step 3: Commit**

```bash
git add tests/test_anchors.py
git commit -m "test: pin golden anchor values for esc_etc ETC"
```

---

### Task 3: SNR vs time + noise-floor ceiling

**Files:**
- Create: `tests/test_physics_snr_time.py`

- [ ] **Step 1: Create `tests/test_physics_snr_time.py`**

```python
"""SNR as a function of integration time, in both photon-limited and
systematic-floor-limited regimes.

Measured 2026-06-01:
  - photon-limited (contrast 1e-10, ppgain 1e6): snr(900)=10.513,
    snr(3600)=21.026 -> ratio 2.0000 = sqrt(4).
  - floor-limited (contrast 1e-7, ppgain 1): snr pinned at 0.1000 = C_p/M.
"""
import numpy as np
import pytest

pytest.importorskip("config_stp_esc")
pytest.importorskip("config_um")

from physics_helpers import esc_snr


def test_snr_non_decreasing_in_exp_time():
    times = [600.0, 1200.0, 2400.0, 3600.0, 7200.0]
    snrs = [esc_snr(exp_time=t)[0] for t in times]
    # Monotonically non-decreasing (allow tiny numerical slack).
    for lo, hi in zip(snrs, snrs[1:]):
        assert hi >= lo - 1e-9


def test_sqrt_time_scaling_photon_limited():
    # Deep contrast + huge ppgain drive the systematic floor M ~ 1e-9, so the
    # planet is photon-limited and SNR ~ sqrt(exp_time).
    deep = dict(contrast=1e-10, ppgain=1e6)
    snr_900, _ = esc_snr(exp_time=900.0, **deep)
    snr_3600, _ = esc_snr(exp_time=3600.0, **deep)
    assert snr_3600 / snr_900 == pytest.approx(np.sqrt(4.0), rel=1e-3)


def test_noise_floor_ceiling_saturation():
    # Shallow contrast + no post-processing gain: M dominates, SNR saturates at
    # the analytic ceiling C_p / M and stops growing with time.
    floor = dict(contrast=1e-7, ppgain=1.0)
    snr_short, esc = esc_snr(exp_time=3600.0, **floor)
    snr_long, _ = esc_snr(exp_time=14400.0, **floor)

    # Saturated: 4x the time barely moves SNR.
    assert abs(snr_long - snr_short) / snr_short < 1e-2

    # Stays at/under the analytic systematic-floor ceiling C_p / M.
    ceiling = esc.source_counts.value / esc.speckle_counts.value / esc.ppgain
    assert snr_long <= ceiling * (1 + 1e-6)
    assert snr_long == pytest.approx(ceiling, rel=1e-2)
```

> Note: internally `esc.ppgain` is the post-processing *factor* (1/input), so the
> floor rate is `speckle_counts * esc.ppgain` and the ceiling is
> `source_counts / (speckle_counts * esc.ppgain)`.

- [ ] **Step 2: Run**

Run: `python -m pytest tests/test_physics_snr_time.py -q`
Expected: `3 passed`.

- [ ] **Step 3: Commit**

```bash
git add tests/test_physics_snr_time.py
git commit -m "test: SNR vs time + noise-floor ceiling invariants"
```

---

### Task 4: Magnitude / flux scaling + monotonicity

**Files:**
- Create: `tests/test_physics_scaling.py`

- [ ] **Step 1: Create `tests/test_physics_scaling.py`**

```python
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

pytest.importorskip("config_stp_esc")
pytest.importorskip("config_um")

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
```

- [ ] **Step 2: Run**

Run: `python -m pytest tests/test_physics_scaling.py -q`
Expected: `5 passed`.

- [ ] **Step 3: Commit**

```bash
git add tests/test_physics_scaling.py
git commit -m "test: magnitude/flux scaling laws and monotonicity"
```

---

### Task 5: Contrast / ppgain / separation

**Files:**
- Create: `tests/test_physics_coronagraph.py`

- [ ] **Step 1: Create `tests/test_physics_coronagraph.py`**

```python
"""Coronagraphic knobs: contrast, post-processing gain, and separation.

Measured 2026-06-01: speckle_counts is linear in contrast (1e-9/1e-8/1e-7 ->
0.0916/0.9158/9.158); noise floor M = speckle_counts * (1/ppgain_input), and
esc.ppgain == 1/ppgain_input (input 10 -> 0.1).
"""
import pytest

pytest.importorskip("config_stp_esc")
pytest.importorskip("config_um")

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
```

- [ ] **Step 2: Run**

Run: `python -m pytest tests/test_physics_coronagraph.py -q`
Expected: `5 passed`.

- [ ] **Step 3: Commit**

```bash
git add tests/test_physics_coronagraph.py
git commit -m "test: contrast/ppgain/separation coronagraph invariants"
```

---

### Task 6: Backgrounds + units/sanity

**Files:**
- Create: `tests/test_physics_backgrounds_units.py`

- [ ] **Step 1: Create `tests/test_physics_backgrounds_units.py`**

```python
"""Background scaling, unit/sanity checks, and saturation-time behavior.

Backgrounds are surface brightnesses in mag/arcsec^2: a *smaller* bg_flux /
exobg_flux number is *brighter* and yields more sky/exozodi counts.
"""
import astropy.units as u
import pytest

pytest.importorskip("config_stp_esc")
pytest.importorskip("config_um")

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
```

- [ ] **Step 2: Run**

Run: `python -m pytest tests/test_physics_backgrounds_units.py -q`
Expected: `6 passed`. If `test_saturation_time_drops_as_source_brightens` fails, check whether `calc_saturation_time()` keys off `source_counts` vs `hoststar_counts` in this config and adjust the brightened knob accordingly (use systematic-debugging; do not weaken the assertion blindly).

- [ ] **Step 3: Commit**

```bash
git add tests/test_physics_backgrounds_units.py
git commit -m "test: background scaling, units/sanity, saturation time"
```

---

### Task 7: Migrate `test_snr.py` to esc_etc

**Files:**
- Modify: `tests/test_snr.py`

- [ ] **Step 1: Replace the entire contents of `tests/test_snr.py`**

```python
import numpy as np
import pytest

pytest.importorskip("config_stp_esc")
pytest.importorskip("config_um")

import esc_etc
import esc_etc.ExposureTimeSNRCalculatorESC


def test_snr():
    # esc_etc.esc_calc_snr returns (snr, esc); value re-derived for esc_etc
    # (the old stp_etc_esc value 2.279 does not carry over).
    snr, _esc = esc_etc.ExposureTimeSNRCalculatorESC.esc_calc_snr(
        600, 10, verbose=False, plot=False
    )
    val = 1.9043539347453955
    assert np.abs(float(snr) - val) < 1e-4, f"Expected {val}, but got {snr}"
```

- [ ] **Step 2: Run**

Run: `python -m pytest tests/test_snr.py -q`
Expected: `1 passed`. If the value differs, update `val` to the printed result (it is a characterization anchor, not a spec requirement).

- [ ] **Step 3: Commit**

```bash
git add tests/test_snr.py
git commit -m "test: migrate test_snr to esc_etc (tuple return, refreshed anchor)"
```

---

### Task 8: Migrate `test_esc_etc_initialization.py` to esc_etc

**Files:**
- Modify: `tests/test_esc_etc_initialization.py`

This file keeps its independent analytic cross-check (`Cp_Cb_M`,
`test_validate_ETC_snr_calculation`) — that is the cross-check-vs-analytic
layer. Only the import and the hardcoded golden numbers change.

- [ ] **Step 1: Repoint the import**

Modify `tests/test_esc_etc_initialization.py:30`:

```python
# before:
from stp_etc_esc import ExposureTimeSNRCalculatorESC as etsc
# after:
from esc_etc import ExposureTimeSNRCalculatorESC as etsc
```

- [ ] **Step 2: Refresh the golden values in `test_counts`**

In the `if telescope == "STP" or telescope == "test_STP":` block of
`test_counts` (around `tests/test_esc_etc_initialization.py:152-159`), replace
the `stp_etc_esc` goldens with the `esc_etc` values measured 2026-06-01:

```python
    if telescope == "STP" or telescope == "test_STP":
        assert round(obs.source_counts.value, 3) == 0.916
        assert round(obs.sky_counts.value, 7) == 0.0002276
        assert round(obs.calc_SNR(600.0 * u.s, 10.0 * u.s), 2) == 2.90
        inttimecalc, noiseterms = obs.calc_int_time(5, 10 * u.s)
        assert round(inttimecalc.value) == round(inttimecalc.value)  # placeholder; pin in step 3
        assert round(obs.calc_saturation_time().value) == round(obs.calc_saturation_time().value)  # pin in step 3
```

- [ ] **Step 3: Pin the remaining two goldens from a real run**

Run this to print the exact `calc_int_time` and `calc_saturation_time` values
under esc_etc, then replace the two placeholder lines above with the printed
integers:

```bash
python - <<'PY'
import matplotlib; matplotlib.use("Agg")
import astropy.units as u
from esc_etc import ExposureTimeSNRCalculatorESC as etsc
obs = etsc.Observatory("STP", 2.4*u.m, 36.45*u.m)
obs.make_STP(); obs.set_generic_source(1e-8, 0)
obs.set_background(background_file=None, plot=False)
obs.make_observation(hoststarflux=-0.353, planetdeltamag=20, bg_flux=22.5,
                     flux_units="vega", plot=False, exobg_flux=21)
it, _ = obs.calc_int_time(5, 10*u.s)
print("inttime =", round(it.value))
print("sattime =", round(obs.calc_saturation_time().value))
PY
```

Replace the two placeholder assertions with, e.g.:

```python
        assert round(inttimecalc.value) == <inttime printed above>
        assert round(obs.calc_saturation_time().value) == <sattime printed above>
```

- [ ] **Step 4: Run the migrated file**

Run: `python -m pytest tests/test_esc_etc_initialization.py -q`
Expected: all tests pass. If `test_validate_ETC_snr_calculation` (the analytic
cross-check) fails, that is a substantive physics discrepancy between the ETC
and the independent `Cp_Cb_M` model — investigate with systematic-debugging;
do not loosen the 0.5% tolerance to force a pass.

- [ ] **Step 5: Commit**

```bash
git add tests/test_esc_etc_initialization.py
git commit -m "test: migrate initialization/cross-check tests to esc_etc"
```

---

### Task 9: Full-suite green + cleanup

**Files:**
- Delete: `tests/test_physics_smoke.py`
- Modify: `docs/superpowers/specs/2026-06-01-esc-etc-physics-tests-design.md` (status)

- [ ] **Step 1: Remove the temporary smoke test**

```bash
git rm tests/test_physics_smoke.py
```

- [ ] **Step 2: Run the entire suite**

Run: `python -m pytest tests/ -q`
Expected: all tests pass (new physics files + migrated files + the existing
config/version tests). Note any skips (e.g. missing config repos) in the commit
message rather than silencing them.

- [ ] **Step 3: Mark the spec status Done**

Edit `docs/superpowers/specs/2026-06-01-esc-etc-physics-tests-design.md:5`:
change `**Status:** Approved (pending spec review)` to `**Status:** Implemented`.

- [ ] **Step 4: Commit**

```bash
git add -A
git commit -m "test: remove temporary smoke test; mark physics-test spec implemented"
```

- [ ] **Step 5: Report**

Print the final `python -m pytest tests/ -q` summary line (counts of passed/skipped) so the result is verifiable, then use superpowers:finishing-a-development-branch to decide merge/PR.

---

## Self-review (completed by plan author)

- **Spec coverage:** SNR-vs-time + ceiling → Task 3; magnitude/flux/area → Task 4 (area replaced per spec note); contrast/ppgain/separation → Task 5; backgrounds/units/sanity → Task 6; anchors → Task 2; migration → Tasks 7–8. All spec sections covered.
- **Placeholders:** the only intentional placeholders are the two `calc_int_time`/`calc_saturation_time` goldens in Task 8, which cannot be known without a run; Task 8 Step 3 provides the exact command to pin them. All test code is otherwise complete.
- **Type/name consistency:** `esc_snr` returns `(float, Observatory)` everywhere; `esc.ppgain` used consistently as the 1/input factor; attribute names (`source_counts`, `sky_counts`, `speckle_counts`, `exozodi_counts`, `num_psf_pixels`) match the probed API.
