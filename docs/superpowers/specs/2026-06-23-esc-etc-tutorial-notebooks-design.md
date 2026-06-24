# esc-etc Tutorial Notebook Suite — Design Spec

**Date:** 2026-06-23
**Status:** Approved for planning
**Author:** Gummi (with Claude Code)

## 1. Goal

Add a suite of four numbered Jupyter tutorial notebooks that teach the new
object-oriented `esc_etc` API and the lazuli-styled plotting helpers, mirroring
wcc-etc's `01_…`–`06_…` tutorial style. They replace the ad-hoc legacy-API demo
notebooks as the canonical "how to use the code" reference.

Builds on the OO architecture
([[../specs/2026-06-23-esc-etc-oo-architecture-design]]) and the plotting helpers
([[../specs/2026-06-23-esc-etc-lazuli-plotting-design]]).

## 2. Decisions (locked)

1. **Four notebooks**, numbered, **directly in `notebooks/`** (mirrors wcc-etc):
   `01_getting_started.ipynb`, `02_components_and_parameters.ipynb`,
   `03_coronagraph_and_contrast.ipynb`, `04_integration_time_snr_saturation.ipynb`.
2. **Existing ad-hoc notebooks left untouched** (`ESC_ExposureTimeSNRCalculator_Demo*.ipynb`,
   `etc_esc_requirements.py`, the dated `2025…`/`2026…` notebooks). No moves/deletes.
3. **Built with the `notebook-demo` skill:** each notebook is authored as a Python
   builder script, executed headless, outputs embedded, and verified (no errors +
   expected sanity values).
4. **Executed `.ipynb` only — no PDFs** in this effort (the skill can export later).
5. **No separate "plotting" notebook** — the five `plot_*` helpers are demonstrated
   in context across 01–04 (YAGNI).
6. **Notebook execution is NOT added to the pytest suite** (too slow + config-
   dependent for CI); the `notebook-demo` build/execute step is the verification gate.

## 3. Conventions (all notebooks)

- Title + intro markdown; numbered section markdown between code cells; a short
  "what you learned / next" closing markdown.
- First code cell: imports + `from esc_etc import use_lazuli_style; use_lazuli_style()`
  so every figure carries the lazuli style.
- Use the **new OO API only** (`Simulation`, `Telescope`, `Sensor`, `Scene`,
  `Coronagraph`, `get_scene`, the `plot_*` helpers). Do not use the deprecated
  `Observatory`/`esc_calc_snr`.
- Require the config repos (`config_um`, `config_stp_esc`) — same as the package.
  Each notebook runs in tens of seconds.
- Figures via the lazuli plotting helpers; close figures are unnecessary in a
  notebook (kept simple).
- Each notebook prints (and states in markdown) at least one **sanity value** so a
  reader can confirm their environment reproduces the reference numbers.

## 4. Per-notebook content

### 01 — Getting started (`01_getting_started.ipynb`)
- `import esc_etc`; `sim = Simulation.from_default(hoststarmag=-0.353,
  planetdeltamag=20, contrast=1e-8, ppgain=10, separation=0.4)`.
- `out = sim.get_snr(total_time=3600*u.s, frame_time=100*u.s)`; explain the result
  dict keys (`snr`, `signal_e`, `noise_e`, `M`).
- `rates = sim.count_rate_components()`; print the contributors.
- `plot_count_rates(sim)`.
- **Sanity:** baseline `out["snr"] ≈ 8.92`.

### 02 — Components & parameters (`02_components_and_parameters.ipynb`)
- Build and inspect each component: `t = Telescope.from_default()` (diameter,
  surface, f_num, resel); `s = Sensor.from_default(t)` (gain, read_noise,
  dark_current, num_psf_pixels == 225, bandpass); `scene = get_scene(t, …)`;
  `c = Coronagraph.from_default(t, …)`.
- Assemble: `sim = Simulation.from_components(t, s, scene, c)`.
- Vary parameters via `update()`: `scene.update(star__mag=2.0)`,
  `c.update(ppgain=100)`; show the SNR/counts change; `reset()`.
- `plot_bandpass(sim)` and `plot_spectra(sim.scene)`.
- **Sanity:** `s.num_psf_pixels.value == 225`.

### 03 — Coronagraph & contrast (`03_coronagraph_and_contrast.ipynb`)
- Explain the coronagraph model: `raw_dh_contrast` → speckle rate,
  `ppgain` → post-processing noise floor, `separation` → off-axis (FPM) throughput.
- Sweep `contrast` (1e-7/1e-8/1e-9), `ppgain` (1/10/100), and `separation`; tabulate/
  plot the SNR response and identify the speckle-floor regime.
- `plot_offaxis_throughput(sim)`.
- **Sanity:** higher `ppgain` → higher SNR; smaller `contrast` → higher SNR;
  `sim.coronagraph.off_axis_throughput(0.4) ≈ 0.543`.

### 04 — Integration time, SNR & saturation (`04_integration_time_snr_saturation.ipynb`)
- `get_snr` at a chosen time; then `get_int_time_for_snr(target_snr, frame_time)` and
  show it recovers the integration time (inverse relationship).
- `plot_snr_vs_time(sim)` — photon-limited rise vs the ppgain-set speckle plateau.
- `sim.saturation_time()` and `sim.is_saturated(frame_time)`.
- **Sanity:** feeding `get_snr`'s SNR back into `get_int_time_for_snr` recovers the
  original `total_time` (to ~1e-3).

## 5. Build & verification (per notebook)

Using the `notebook-demo` skill:
1. Author a Python builder script that emits the notebook cells (markdown + code).
2. Execute the notebook headless end-to-end.
3. Confirm: zero execution errors; the stated sanity value is printed/correct.
4. Embed outputs and save the `.ipynb`.

A notebook is "done" only when it executes cleanly and reproduces its sanity value.

## 6. Docs

- Add a **"Tutorials"** section to `README.md` listing the four notebooks with a
  one-line description each, and noting they use the new OO API (the older demo
  notebook reference may remain, marked legacy).
- Add a `docs/ETC_Changelog.rst` entry recording the tutorial suite.

## 7. Out of scope (YAGNI)

- No PDF export (skill can do it later).
- No 5th plotting-only notebook.
- No changes to the OO engine, plotting module, or the compat shim.
- No moving/deleting the existing ad-hoc notebooks.
- No CI/pytest notebook-execution job.

## 8. Risks

- **Config dependency:** notebooks require `config_um`/`config_stp_esc` and the
  editable install (`pip install -e .` — see [[../../../MEMORY]]); they will not run
  in an environment lacking those. The intro markdown notes this requirement.
- **Sanity-value drift:** the pinned numbers (SNR ≈ 8.92, num_psf_pixels 225,
  off-axis ≈ 0.543) come from the current config; if configs change, update the
  notebooks. They mirror the values already pinned in the test suite, so drift is
  caught there too.
- **Execution time:** four config+synphot runs make a full rebuild take a few
  minutes; acceptable for a docs build, not for CI (hence decision 6).
