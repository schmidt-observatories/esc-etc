# esc-etc Object-Oriented Architecture — Design Spec

**Date:** 2026-06-23
**Status:** Approved for planning
**Author:** Gummi (with Claude Code)

## 1. Goal

Rewrite `esc_etc` into a compositional, object-oriented architecture that mirrors
`wcc-etc` v0.6.0, while preserving ESC's validated coronagraph physics. Today ESC
is a single monolithic `Observatory` class (~1350 lines) with a procedural
`esc_calc_snr()` wrapper. The target is a clean set of composable components —
`Telescope`, `Sensor`, `Scene`, `Coronagraph`, orchestrated by a `Simulation` —
following the same patterns, factories, and unit conventions as wcc-etc.

The new architecture must reproduce every existing golden-anchor SNR value and
scaling law (the `add-physics-tests` suite), by construction.

## 2. Decisions (locked)

These were settled during brainstorming and are not open for re-litigation during
implementation:

1. **Full native rewrite** mirroring wcc-etc's structure (not an adapter, not a
   wrapper-only layer). The physics is reimplemented inside the new classes.
2. **Standalone mirror.** `esc_etc` gets its own `_MetaHolder_` / `Telescope` /
   `Sensor` / `Scene` classes copying wcc-etc's patterns. **No dependency on
   `wcc_etc`.** The two packages evolve independently.
3. **Analytic SNR engine now, pluggable 2D-PSF hook later.** The default engine is
   ESC's existing analytic count-rate + speckle/ppgain model, placed behind a
   `noise_model` seam so a 2D coronagraphic PSF image path can be added later
   without restructuring.
4. **Keep `esc_calc_snr()` / `Observatory` as a thin deprecated compat shim** that
   delegates to the new objects. The existing physics test suite keeps passing
   unchanged and becomes the regression guard. Remove the shim in a later release.
5. **Wrap the uasal config repos behind `from_config` factories.** Keep depending on
   `config_stp_esc` / `config_um` as the source of truth; do not port to local TOML.
6. **Scene element naming: `star` / `planet` / `zodi` / `exozodi`** (not wcc's
   `source` / `host`). The planet is the measured source; the star is the host.

## 3. Architecture overview

```
Scene  (star, planet, zodi, exozodi) ┐
Sensor (detector + optical bandpass) ┤
Telescope (aperture geometry)        ├─→ Simulation ─→ get_snr() ─→ {snr, signal, noise terms, ...}
Coronagraph (contrast, ppgain,       ┘                ├─→ get_int_time_for_snr()
             off-axis λ/D throughput)                 └─→ is_saturated() / saturation_time()
```

- `Simulation` *has-a* `Telescope`, `Sensor`, `Scene`, `Coronagraph` (strong
  composition; mirrors wcc's `Simulation`).
- `Scene` *has-a* `star`, `planet`, and background elements `zodi`, `exozodi`
  (weak composition; backgrounds optional).
- `Telescope`, `Sensor`, `Coronagraph` are stateless-ish instrument descriptions;
  `Scene` carries observable state.
- All major classes inherit `_MetaHolder_` for consistent `update()` / `reset()` /
  `describe()` semantics and `name__param=` fluent routing.

## 4. Components

New `esc_etc` modules (under `src/esc_etc/`):

### 4.1 `meta.py` — `_MetaHolder_`
Copied pattern from wcc-etc. Provides:
- `meta : dict` — current parameter values.
- `mutable_parameters : list` — allowed update keys (declared per subclass).
- `update(**kwargs)` — update mutable params; supports nested `name__param=` routing
  to sub-elements; returns updated keys; invalidates caches.
- `reset()` — revert to initial parameters.
- `describe()` — print current parameter values.

### 4.2 `telescope.py` — `Telescope(_MetaHolder_)`
Aperture geometry only (throughput lives in `Sensor`, mirroring wcc).
- Properties: `diameter_primary` (m), `f_num`, `focal_len`, collecting `surface`
  (π(D/2)² minus obscuration), M1/M2 obscuration fraction/diameter.
- `from_config(config)` — read geometry from `config_um` (Ultramarine 3 m telescope).

### 4.3 `sensor.py` — `Sensor(_MetaHolder_)`
Detector physics + total non-coronagraph optical throughput.
- Properties: `gain` (e⁻/ADU), `read_noise` (e⁻/pix RMS), `dark_current`
  (e⁻/s/pix), `well_depth`, `pixel_size` (μm/pix), `num_pixels`,
  `num_psf_pixels`, `plate_scale` (computed from telescope geometry), `bandpass`
  (synphot `SpectralElement`: mirrors + filter + QE).
- The `bandpass` is built by accumulating the optical train (the current
  `add_mirror` / `add_transmissive_optic` / `add_sensor` logic) — but **excluding**
  the coronagraph-specific λ/D throughput, which moves to `Coronagraph`.
- `from_config(config)` — read detector + optics specs from `config_stp_esc`.
- `get_plate_scale(telescope)` — arcsec/pix from telescope + pixel pitch.

### 4.4 `scene.py` — `SceneElement` + `Scene(_MetaHolder_)`
- `SceneElement(_MetaHolder_)`: one observational element (spectrum + magnitude),
  built on synphot. Methods mirror wcc: `set_spectrum()`, `get_spectrum()`,
  `get_observation(band=...)`, `get_mag()`, `update()`, `show()`. Supports file
  spectra (Pickles stellar library), parametric spectra, and surface-brightness
  handling for backgrounds.
- `Scene(_MetaHolder_)`: composite holding named elements `star`, `planet`,
  `zodi`, `exozodi`.
  - `star` — host star (anchor magnitude).
  - `planet` — measured source; defined relative to `star` via `planetdeltamag`
    (and/or `contrast`).
  - `zodi`, `exozodi` — background surface-brightness elements.
  - Methods: `get_elements(which='*')`, `get_mag(...)`, `get_spectrum(...)`,
    `get_observation(...)`, `update()` with `star__mag=` / `planet__deltamag=` /
    `zodi__mag=` routing, `reset()`.
- Top-level factory `get_scene(...)` mirroring wcc's convenience constructor.

### 4.5 `coronagraph.py` — `Coronagraph(_MetaHolder_)` (new component)
Carries all coronagraph-specific physics that has no analog in the wide-field WCC.
- Properties: `raw_dh_contrast` (raw dark-hole contrast, e.g. 1e-8), `ppgain`
  (post-processing gain), `separation` (planet position, arcsec or λ/D), off-axis /
  FPM throughput curve (from the `add_lamD_optic` λ/D lookup table), `iwa`, `owa`.
- Methods:
  - `off_axis_throughput(separation)` — interpolate the FPM/off-axis throughput at
    the planet separation (nearest-λ/D lookup, as today).
  - `speckle_scale()` — scale factor turning host-star count rate into residual
    speckle count rate from `raw_dh_contrast`.
  - `noise_floor(speckle_counts)` — post-processing residual floor
    `M = speckle_counts / ppgain`.
- `from_config(config)` — read coronagraph specs from `config_stp_esc`.

### 4.6 `simulation.py` — `Simulation(_MetaHolder_)`
Top-level orchestrator and primary user entry point.
- Factories: `from_components(telescope, sensor, scene, coronagraph)`,
  `from_config(config)`.
- `count_rate_components()` → dict of star / planet / zodi / exozodi / speckle
  count rates (Quantities, e⁻/s). Planet rate includes
  `coronagraph.off_axis_throughput(separation)`. Speckle rate uses
  `coronagraph.speckle_scale()`.
- `get_snr(int_time, exp_time)` → dict `{snr, signal_e, noise_e, <noise terms>}`.
- `get_int_time_for_snr(snr, exp_time)` → dict `{int_time_s, ...}`.
- `is_saturated(exp_time)` → bool; `saturation_time()` → Quantity.
- `update()` routes to sub-components (`star__mag=`, `coronagraph__ppgain=`,
  `sensor__read_noise=`, ...).
- **`noise_model` seam:** the analytic math lives in a `noise_model` attribute,
  default `AnalyticCoronagraphNoiseModel`, which consumes `count_rate_components()`
  + detector noise and returns SNR / int-time. This is the future hook for a 2D
  coronagraphic PSF image path; swapping it must not require touching `Simulation`'s
  public API.

### 4.7 `compat.py` — deprecated shim
- `Observatory` and `esc_calc_snr(...)` preserved with current signatures and the
  `(snr, observatory)` tuple return. Internally they build the new
  `Scene`/`Sensor`/`Telescope`/`Coronagraph`/`Simulation` objects and delegate.
- Emit `DeprecationWarning` pointing at the new API.
- Slated for removal in a later release (tracked separately).

### 4.8 `__init__.py`
Public exports: `Simulation`, `Telescope`, `Sensor`, `Scene`, `SceneElement`,
`Coronagraph`, `get_scene`, `AnalyticCoronagraphNoiseModel`, plus the deprecated
`Observatory` / `esc_calc_snr` from `compat`.

## 5. Coronagraph physics mapping

The current tangled `Observatory` knobs map onto the new components as follows:

| Today (`Observatory`) | New home |
|---|---|
| `set_rawDH_contrast(contrast)` | `Coronagraph.raw_dh_contrast` |
| `ppgain` → `M = speckle_counts / ppgain` | `Coronagraph.ppgain` / `Coronagraph.noise_floor()` |
| `separation` + `add_lamD_optic(...)` | `Coronagraph.off_axis_throughput(separation)` |
| `speckle_counts = host_countrate × scale` | `Coronagraph.speckle_scale()` × star rate |
| `set_generic_source(contrast, starMag)` | `Scene.star.mag` + `Scene.planet.deltamag`/`contrast` |
| `set_background(...)` (zodi/exozodi) | `Scene.zodi`, `Scene.exozodi` |
| `make_STP(...)` optical train | `Sensor.bandpass` (non-corona) + `Coronagraph` (corona) |
| `calc_SNR` / `calc_int_time` | `AnalyticCoronagraphNoiseModel` inside `Simulation` |

`Simulation` asks `Coronagraph` for off-axis throughput, speckle scale, and the
post-processing floor, then folds them into the analytic SNR exactly as the current
`calc_SNR` / `calc_int_time` do — so the golden anchors are reproduced by
construction, not by re-derivation.

## 6. Units

Follow ESC + wcc conventions: astropy + synphot units throughout. Magnitudes as
`Quantity` (VEGAMAG / ABmag), wavelengths in nm/Å, count rates `electron/s`,
`electron/s/pix`, dark current `electron/(s·pix)`, read noise `electron/pix`,
time in seconds, plate scale `arcsec/pix`, separation in arcsec (with λ/D helpers).
Bare floats passed to constructors are auto-attached to canonical units.

## 7. Backward compatibility & testing

### 7.1 Regression guard
The entire existing `add-physics-tests` suite drives `esc_calc_snr()` / `Observatory`.
With the compat shim delegating to the new engine, this suite runs **unchanged** and
proves the new classes reproduce every anchor (e.g. baseline SNR = 8.9221), scaling
law (delta-mag, host-mag flux laws), coronagraph-knob monotonicity (contrast,
ppgain, separation), background scaling, unit consistency, and saturation behavior.

### 7.2 New tests
- Per-class unit tests: `test_meta.py`, `test_telescope.py`, `test_sensor.py`,
  `test_scene.py`, `test_coronagraph.py`, `test_simulation.py`.
- **Equivalence test** (`test_api_equivalence.py`): assert the new
  `Simulation` API and the `esc_calc_snr` shim produce identical SNR / int-time
  across a parameter grid (exp_time, int_time, host mag, contrast, planetdeltamag,
  ppgain, separation, backgrounds). Tight tolerance (floating-point identical or
  within 1e-9 relative).
- `noise_model` seam test: a trivial alternate `noise_model` can be injected and is
  actually called by `Simulation`.

### 7.3 Methodology
Implementation is **TDD-driven** (write/port the test, watch it fail, implement).
Build bottom-up: `_MetaHolder_` → `Telescope` / `Sensor` → `Scene` → `Coronagraph`
→ `Simulation` → `compat` shim. The regression suite is wired to the shim only after
`Simulation` is functional.

## 8. Out of scope (YAGNI)

- No 2D coronagraphic PSF image simulator now (only the `noise_model` seam for it).
- No separate `OpticalTrain` component — coronagraph throughput lives in
  `Coronagraph`, the rest in `Sensor.bandpass`.
- No porting uasal configs to local TOML.
- No changes to the `wcc-etc` repo.
- No web/Flask interface work in this effort.

## 9. Risks

- **Config-repo coupling:** `from_config` factories depend on `config_stp_esc` /
  `config_um` git deps and the `pip install -e .` editable-install requirement
  (a plain `pip install .` shadows the repo). Document and keep editable install.
- **Anchor drift:** any numerical reorganization (e.g. order of operations in count
  rates) could perturb anchors. Mitigation: equivalence test + unchanged regression
  suite catch this immediately.
- **synphot spectrum sourcing:** stellar spectra come from the UASAL archive; the
  `Scene`/`SceneElement` rewrite must preserve the same resampling
  (`resample_SpectralElement` / `resample_SourceSpectrum`) behavior.
