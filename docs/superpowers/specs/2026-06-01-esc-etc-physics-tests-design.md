# ESC ETC Physics Test Suite — Design

**Date:** 2026-06-01
**Status:** Approved (pending spec review)
**Author:** Gummi + Claude

## Goal

Add a comprehensive, physics-based test suite for the ESC Exposure Time
Calculator so that regressions and configuration drift are caught automatically.
Tests assert physical relationships and scaling laws (robust to config tweaks),
backed by a small set of pinned "golden" anchor values.

## Background / current state

- The ETC lives in `src/esc_etc/ExposureTimeSNRCalculatorESC.py`, package
  `esc_etc` (now installed **editable** → imports resolve to the repo source).
- High-level entry point: `esc_calc_snr(exp_time, int_time, hoststarmag=-0.353,
  contrast=1e-8, planetdeltamag=20, bg_flux=22.5, exobg_flux=21,
  flux_units='vega', separation=0.2, ppgain=10, verbose=True, plot=False)`.
  It returns a **`(snr, esc)` tuple**, where `esc` is the configured
  `Observatory` instance.
- Low-level API (used for area-scaling and the existing tests):
  `Observatory(name, diameter, focal_len)` → `make_STP()` →
  `set_generic_source(contrast, starMag)` → `set_background()` →
  `make_observation(...)` → `calc_SNR(int_time, exp_time)`,
  `calc_saturation_time()`, `calc_int_time(snr, exp_time)`.
- Existing tests under `tests/` import the **twin** package `stp_etc_esc`
  (`test_esc_etc_initialization.py`, `test_snr.py`). They include a strong
  independent analytic cross-check (`Cp_Cb_M`) and golden values.

### Empirically confirmed behavior (probe, 2026-06-01)

All directions below were verified against the live `esc_etc` implementation, so
the invariant tests assert real behavior:

- `source_counts` follows `10^(-0.4·Δmag)` exactly (each 2-mag step = ×6.31).
- `speckle_counts` is linear in `contrast`.
- Noise floor `M = speckle_counts / ppgain_input` (input `ppgain=10` →
  internal `esc.ppgain = 0.1`).
- SNR is non-decreasing in `exp_time`; **saturates** toward the systematic floor
  when the floor dominates (doubling 3600→7200 s moved SNR only 8.92→9.42 at
  baseline). ⇒ sqrt(t) scaling must be tested in a *photon-limited* regime
  (deep contrast / high ppgain); saturation in a *floor-limited* regime.
- Anchor: `esc_calc_snr(3600, 100, separation=0.4, contrast=1e-8, ppgain=10)`
  → `snr ≈ 8.9221`.
- One full `esc_calc_snr` call ≈ 0.4 s.

## Scope (agreed)

- **Target package:** `esc_etc`, and **migrate** the existing
  `stp_etc_esc`-based tests to `esc_etc`.
- **Style:** physics invariants + a few pinned golden anchors.
- **Coverage areas (all four):**
  1. SNR vs integration time + noise-floor ceiling
  2. Magnitude / flux / collecting-area scaling
  3. Contrast, ppgain, separation
  4. Backgrounds + units/sanity

## Architecture

Themed test files (small, independently runnable) plus a shared fixture module
and an isolated anchors file. All under `tests/`.

### `tests/conftest.py` (new)
- `snr_case(**overrides)` — calls `esc_etc.ExposureTimeSNRCalculatorESC.esc_calc_snr`
  with a single canonical baseline dict (`verbose=False, plot=False`), applies
  overrides, returns `(snr, esc)`. Single source of truth for the baseline.
- `@lru_cache` memoization keyed on the frozen kwargs so repeated identical
  configs across tests don't recompute (keeps the suite < ~30 s).
- Headless setup: `matplotlib.use("Agg")`.
- Skip guard: `pytest.importorskip` / try-import for `config_stp`,
  `config_stp_esc`, `config_um`, `utils_config` so missing config repos skip
  rather than error (mirrors existing tests).

### `tests/test_physics_snr_time.py` (new)
- SNR non-decreasing across an `exp_time` grid.
- Photon-limited regime (deep contrast + high ppgain so floor negligible):
  `SNR ∝ sqrt(exp_time)` within tolerance over a grid.
- Floor-limited regime (shallow contrast / low ppgain): SNR saturates
  (relative change small over a large exp_time increase) and stays below the
  analytic ceiling `C_p / M`.

### `tests/test_physics_scaling.py` (new)
- `source_counts` ratio for `Δplanetdeltamag = 2.5` ≈ 10 (and a 5-mag step
  ≈ ×100), within tolerance.
- Monotonic: fainter planet (larger `planetdeltamag`) → lower SNR over a grid.
- Host-magnitude flux law: at fixed `planetdeltamag`, `source_counts ∝
  10^(-0.4·hoststarmag)` — a 2.5-mag brighter host → ×10 counts, within
  tolerance. (Replaces the originally-planned collecting-area `D²` test — see
  note below.)
- Brighter host (smaller `hoststarmag`) → higher `source_counts` / SNR.

> **Note (probe finding, 2026-06-01):** the `Observatory(name, diameter,
> focal_len)` constructor arguments are **overridden by the telescope config in
> `make_STP()`** — varying the constructor diameter/focal length changes neither
> `source_counts`, `plate_scale`, nor `num_psf_pixels`. Collecting area is
> therefore **not** a free knob through the public API, so the `counts ∝ D²`
> test is not implementable as designed and is replaced by the host-magnitude
> flux law above (same underlying `F0·10^(-0.4·mag)·area·throughput` physics,
> exercised through a knob the API actually controls).

### `tests/test_physics_coronagraph.py` (new)
- Deeper contrast → higher SNR; `speckle_counts` linear in contrast.
- Higher ppgain → higher SNR; `M == speckle_counts / ppgain_input`
  (equivalently `esc.ppgain == 1/ppgain_input`).
- Separation: throughput/SNR varies with `separation` via the λ/D mask curve.
  Assert robust properties (SNR finite/positive and changes across a separation
  grid; direction consistent with the mask within its designed working angle) —
  not a fragile exact shape.

### `tests/test_physics_backgrounds_units.py` (new)
- Brighter zodi (smaller `bg_flux` mag) → higher `sky_counts` → lower SNR.
- Brighter exozodi (smaller `exobg_flux`) → higher `exozodi_counts`.
- Units/sanity: `source_counts`, `sky_counts`, `speckle_counts`,
  `exozodi_counts` carry `electron/s`; `num_psf_pixels` in `pix`; all
  non-negative; SNR finite and positive.
- `calc_saturation_time()` decreases as the source brightens.

### `tests/test_anchors.py` (new)
- 2–3 pinned golden values to catch uniform regressions that preserve scalings,
  e.g. `esc_calc_snr(3600,100,separation=0.4,contrast=1e-8,ppgain=10) ≈ 8.9221`.
- A low-level baseline anchor (`source_counts` / `sky_counts` / `snr`) carried
  over from the migrated initialization test.
- Pinned at ~1e-3 relative tolerance.

### Migration (in place)
- `test_esc_etc_initialization.py`: swap
  `from stp_etc_esc import ExposureTimeSNRCalculatorESC as etsc` →
  `from esc_etc import ExposureTimeSNRCalculatorESC as etsc`. Re-run; update
  golden values **only if** `esc_etc` genuinely differs from `stp_etc_esc`.
  Keep `Cp_Cb_M` as the independent analytic cross-check.
- `test_snr.py`: swap import to `esc_etc`; unpack the `(snr, esc)` tuple;
  re-verify / update the `2.279` anchor against `esc_etc`.
- Do not keep duplicate `stp_etc_esc` copies of these tests.

## Tolerances & robustness
- Invariants: directional/ratio assertions, tolerances ~1–5%; monotonicity with
  a small epsilon.
- Anchors: ~1e-3 relative tolerance.
- All tests run headless (`Agg`, `verbose=False`, `plot=False`).

## Runtime
- ≈ 0.4 s/call × ~50 calls < ~30 s. `lru_cache` removes duplicate work. Heavy
  parameter sweeps may be marked `@pytest.mark.slow`.

## Dependencies / assumptions
- Requires importable `config_stp`, `config_stp_esc`, `config_um`,
  `utils_config` (as the existing suite does); otherwise tests skip.
- `esc_etc` is editable-installed so imports hit the repo source. NOTE: a
  non-editable `pip install .` from a stale checkout will re-shadow it; avoid
  that (this was the original `separation` bug).

## Out of scope
- Changing ETC physics or the `esc_calc_snr` API.
- Removing/refactoring the `stp_etc_esc` twin package.
- Performance optimization of the ETC itself.

## Success criteria
- New + migrated tests pass under `pytest` against `esc_etc`.
- Invariant tests have no fragile magic numbers (only ratios/directions +
  a few clearly-labeled anchors).
- Suite runs in well under a minute and is headless/CI-friendly.
