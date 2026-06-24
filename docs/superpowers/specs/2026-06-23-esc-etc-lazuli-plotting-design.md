# esc-etc Lazuli-styled Plotting Helpers — Design Spec

**Date:** 2026-06-23
**Status:** Approved for planning
**Author:** Gummi (with Claude Code)

## 1. Goal

Add a small set of convenience plotting helpers to `esc_etc`, styled with the
canonical **lazuli** matplotlib style, mirroring the conventions of wcc-etc's
`plotting.py`. The helpers cover the plots that matter for an analytic
coronagraph ETC: the count-rate/noise breakdown, SNR vs integration time, the
off-axis (FPM) throughput curve, the instrument bandpass, and the scene spectra.

This builds on the OO architecture (`Simulation`/`Telescope`/`Sensor`/`Scene`/
`Coronagraph`); see [[../specs/2026-06-23-esc-etc-oo-architecture-design]].

## 2. Decisions (locked)

1. **All five helper plots** are in scope: count-rate breakdown, SNR-vs-time,
   off-axis throughput, bandpass, spectra.
2. **Ship `lazuli.mplstyle` inside the package** (`src/esc_etc/data/lazuli.mplstyle`),
   a byte-for-byte copy of the canonical file (currently
   `lazuli-transit/notebooks/lazuli.mplstyle`). No cross-repo path dependency, no
   tweaks to the palette/fonts.
3. **Apply the style via a context manager** so helpers never clobber the user's
   global rcParams. Also expose `use_lazuli_style()` for opt-in global use and the
   named color tokens.
4. **No convenience methods on `Simulation`** — plotting lives entirely in the
   `plotting` module (YAGNI; matches wcc-etc).
5. **Mirror wcc-etc's `plotting.py` API convention:** each helper takes the domain
   object positionally OR explicit raw arrays as keywords, accepts `ax=None`,
   applies the lazuli style, and returns `(fig, ax)`.

## 3. The lazuli style

The canonical `lazuli.mplstyle` (to be copied verbatim):

- Fonts: `mathtext.fontset: stix`, `font.family: STIXGeneral`, `axes.formatter.useoffset: False`.
- Sizes: `axes.labelsize/titlesize 13`, `legend.fontsize 10`, `figure.dpi/savefig.dpi 150`, `savefig.bbox tight`.
- Ticks: inward (`xtick/ytick.direction in`), minor ticks visible, top/right ticks on.
- Grid: on, `alpha 0.3`, `linewidth 0.3`.
- Lines/legend: `lines.linewidth 2.0`, `legend.frameon False`.
- Palette (`axes.prop_cycle`): `00798c, d1495b, edae49, 30638e, 66a182, 003d5b`.

Color tokens exported by the module:
`TEAL="#00798c"`, `RED="#d1495b"`, `AMBER="#edae49"`, `BLUE="#30638e"`,
`GREEN="#66a182"`, `DARKBLUE="#003d5b"`, and `LAZULI_COLORS` (the list in cycle order).

## 4. Module layout

New files:
- `src/esc_etc/plotting.py` — the helpers + style utilities.
- `src/esc_etc/data/lazuli.mplstyle` — shipped style file.

Packaging: add a `[tool.setuptools.package-data]` (or equivalent) entry so
`esc_etc/data/*.mplstyle` is included in the wheel; the path is resolved at
runtime via `importlib.resources.files("esc_etc") / "data" / "lazuli.mplstyle"`.

`matplotlib` is already a core dependency — no new dependency.

## 5. Style utilities (in `plotting.py`)

- `_LAZULI_STYLE_PATH` — resolved via `importlib.resources.files`.
- `lazuli_style()` → returns `plt.style.context(_LAZULI_STYLE_PATH)` (a context
  manager). Every helper wraps its drawing in `with lazuli_style():`.
- `use_lazuli_style()` → `plt.style.use(_LAZULI_STYLE_PATH)` for opt-in global use.
- `_apply_axis_cosmetics(ax)` — applies inward minor+major ticks, top/right ticks,
  and the subtle grid to a given axis, so a **user-supplied** `ax` (whose rcParams
  were fixed at creation) still gets the lazuli look. Called by every helper on the
  axis it draws on.
- Color tokens + `LAZULI_COLORS` as module constants.

## 6. Helper functions

All return `(fig, ax)`. When `ax is None`, the fig/ax are created **inside** the
`lazuli_style()` context so the axis fully inherits the style; when `ax` is given,
the helper draws within the context and calls `_apply_axis_cosmetics(ax)`. Each
uses a small input-resolver: if the domain object is provided, derive the arrays
from it; otherwise use the explicit keyword arrays (so the helper is testable
without loading configs).

1. **`plot_count_rates(sim=None, *, rates=None, sensor=None, ax=None, log=True)`**
   Bar chart of count-rate contributors in e⁻/s: `source`, `zodi`, `exozodi`,
   `speckle`, and dark-current total (`sensor.dark_current * sensor.num_psf_pixels`).
   Resolves from `sim.count_rate_components()` + `sim.sensor`, or from an explicit
   `rates` (`CountRates`) + `sensor`. Bars colored from the palette; `log=True`
   sets a log y-axis (values clipped to a small positive floor for the log scale).
   The matplotlib+lazuli successor to the old Bokeh `plot_compare_fluxes`.

2. **`plot_snr_vs_time(sim=None, *, total_times=None, frame_time=100*u.s, snrs=None, ax=None)`**
   Log-log SNR vs total integration time. If `sim` is given and `snrs` is not,
   sweep `total_times` (default a logspace, e.g. 10–1e5 s) computing
   `sim.get_snr(total_time=t, frame_time=frame_time)["snr"]` for each; otherwise
   plot the supplied `(total_times, snrs)`. Reveals the photon-limited rise and the
   ppgain-set speckle-floor plateau. x in seconds, y is SNR.

3. **`plot_offaxis_throughput(coronagraph=None, *, separations=None, throughputs=None, ax=None, mark_separation=True)`**
   FPM λ/D transmission vs planet separation (arcsec). Accepts a `Coronagraph`, or
   a `Simulation` (uses `sim.coronagraph`), or explicit `(separations, throughputs)`.
   When `mark_separation`, draws a vertical marker at the coronagraph's current
   `separation`. Default `separations` is a linspace spanning the curve's range.

4. **`plot_bandpass(sensor=None, *, wavelength=None, throughput=None, ax=None)`**
   `Sensor.bandpass` throughput vs wavelength. Accepts a `Sensor` (evaluate its
   `bandpass` over its waveset), a `Simulation` (uses `sim.sensor`), or explicit
   `(wavelength, throughput)` arrays. y is dimensionless throughput; x in nm/Å.

5. **`plot_spectra(scene=None, *, which=("star","planet","zodi"), ax=None)`**
   Scene element spectra. Accepts a `Scene`, or a `Simulation` (uses `sim.scene`).
   Plots the named elements' `spectrum` over a sensible wavelength grid, one palette
   color each, with a legend.

## 7. Error handling

- Missing required inputs (neither domain object nor the matching kwargs) raise a
  clear `ValueError` naming what's needed (mirrors wcc's resolver behavior).
- `plot_count_rates` with `log=True` clips non-positive values to a small floor
  (e.g. `1e-30`) before plotting, as the old `plot_compare_fluxes` did.
- Helpers never call `plt.show()` (caller/notebook decides); they only build and
  return `(fig, ax)`.

## 8. Testing

Headless (the existing `tests/conftest.py` forces the Agg backend). Tests assert
behavior, not pixels:

- Each helper returns a `(Figure, Axes)` tuple.
- Expected artist counts (e.g. `plot_count_rates` draws 5 bars; `plot_spectra`
  draws one line per requested element).
- Axis labels are set (non-empty x/y labels).
- The raw-array path works **without** a `Simulation` (pass arrays/`CountRates`
  directly) — keeps tests fast and config-free where possible.
- A lazuli palette color is applied (e.g. first bar facecolor == `TEAL`).
- `lazuli_style()` does not permanently mutate global rcParams (capture a key
  rcParam before/after a `with lazuli_style():` block and assert it's restored);
  `use_lazuli_style()` does change it.
- Color tokens and `LAZULI_COLORS` exist and match the canonical hex values.
- `test_public_api.py` updated to assert the new exports.

A small number of integration-flavored tests may construct a real `Simulation`
via `from_default()` (config-dependent, slower) to exercise the domain-object path
of at least one helper; the rest use the raw-array path.

## 9. Exports

Added to `esc_etc.__init__.__all__`: `plot_count_rates`, `plot_snr_vs_time`,
`plot_offaxis_throughput`, `plot_bandpass`, `plot_spectra`, `lazuli_style`,
`use_lazuli_style`, `LAZULI_COLORS`, `TEAL`, `RED`, `AMBER`, `BLUE`, `GREEN`,
`DARKBLUE`.

## 10. Out of scope (YAGNI)

- No Bokeh/web versions (wcc has them; ESC web portal not in scope here).
- No convenience `Simulation.plot_*` methods.
- No 2D image plots (esc-etc is analytic; there is no SimulatedImage).
- No new style variants or palette edits — ship the canonical lazuli style as-is.
- No changes to the OO engine or the compat shim.

## 11. Risks

- **Package-data inclusion:** if the `.mplstyle` isn't added to the build config it
  won't ship in the wheel; resolve via `importlib.resources` and add the
  package-data entry. Editable installs (`pip install -e .`, the required mode —
  see [[../../../MEMORY]]) read it from the source tree regardless.
- **Style drift:** the shipped copy can drift from the canonical
  `lazuli-transit/notebooks/lazuli.mplstyle`; mitigated by copying verbatim and
  noting the canonical source in a header comment.
- **User-supplied `ax`:** axis-creation rcParams (ticks/grid) won't retroactively
  apply; `_apply_axis_cosmetics(ax)` covers the visible cosmetics.
