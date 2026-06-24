# esc-etc Lazuli-styled Plotting Helpers Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Add a `esc_etc.plotting` module with five lazuli-styled matplotlib helpers (count-rate breakdown, SNR-vs-time, off-axis throughput, bandpass, spectra), mirroring wcc-etc's `plotting.py` conventions.

**Architecture:** A single `plotting.py` module plus a shipped `data/lazuli.mplstyle`. Style is applied per-call via a `lazuli_style()` context manager (with an opt-in global `use_lazuli_style()`); every helper takes the domain object (`Simulation`/`Coronagraph`/`Sensor`/`Scene`) positionally OR explicit raw arrays as keywords, accepts `ax=None`, and returns `(fig, ax)`.

**Tech Stack:** Python ≥3.8, matplotlib (already a core dep), numpy, astropy.units, synphot; builds on the esc_etc OO modules (`simulation`, `noise`, `coronagraph`, `sensor`, `scene`).

## Global Constraints

- Package installed editable: `pip install -e .` (a plain `pip install .` shadows the repo — see MEMORY).
- No new runtime dependency — matplotlib is already in `pyproject` dependencies.
- Ship `src/esc_etc/data/lazuli.mplstyle` **byte-for-byte** from the canonical copy (`lazuli-transit/notebooks/lazuli.mplstyle`); no palette/font tweaks. Add a header comment noting the canonical source.
- Resolve the shipped style at runtime via `importlib.resources.files("esc_etc") / "data" / "lazuli.mplstyle"`.
- Helpers apply the style via the `lazuli_style()` context manager and must NOT permanently mutate global rcParams. `use_lazuli_style()` is the only function allowed to mutate global rcParams.
- Every helper returns `(fig, ax)` and never calls `plt.show()`.
- Color tokens (exact hex): `TEAL="#00798c"`, `RED="#d1495b"`, `AMBER="#edae49"`, `BLUE="#30638e"`, `GREEN="#66a182"`, `DARKBLUE="#003d5b"`; `LAZULI_COLORS = [TEAL, RED, AMBER, BLUE, GREEN, DARKBLUE]`.
- Tests run headless: `tests/conftest.py` already forces the Agg backend. Tests assert behavior (return types, artist counts, labels, colors), never pixels. Prefer the raw-array / config-free path so most tests don't load configs.
- TDD: failing test → run → minimal impl → run → commit. Frequent commits. Do not `git add -A` — add named files.

## esc_etc interfaces these helpers rely on (already implemented)

- `Simulation.count_rate_components() -> CountRates` with fields `source, zodi, exozodi, speckle, host` (all astropy Quantity, e⁻/s).
- `Simulation.get_snr(total_time, frame_time) -> dict` with key `"snr"` (float).
- `Simulation.noise_model.snr(rates, sensor, coronagraph, total_time, frame_time) -> dict` (key `"snr"`).
- `Simulation.sensor` (a `Sensor`): `.dark_current` (e⁻/s/pix), `.num_psf_pixels` (pix), `.bandpass` (synphot `SpectralElement`).
- `Simulation.coronagraph` (a `Coronagraph`): `.off_axis_throughput(separation_arcsec_float) -> float`, `.separation` (float, arcsec).
- `Simulation.scene` (a `Scene`): `.star/.planet/.zodi/.exozodi` (`SceneElement`s), each with `.spectrum` (synphot `SourceSpectrum`) and `.mag`.
- `CountRates` is a dataclass importable as `from esc_etc.noise import CountRates`.
- `SceneElement(name, spectrum, mag, mag_system="vega", deltamag=None)` and `Scene(star, planet, zodi, exozodi)` importable from `esc_etc.scene` (construct directly in tests to avoid configs).

---

### Task 1: Ship the lazuli style + style utilities

**Files:**
- Create: `src/esc_etc/data/lazuli.mplstyle`
- Create: `src/esc_etc/plotting.py`
- Modify: `pyproject.toml` (package-data glob)
- Test: `tests/test_plotting_style.py`

**Interfaces:**
- Produces: `TEAL, RED, AMBER, BLUE, GREEN, DARKBLUE` (str), `LAZULI_COLORS` (list[str]), `lazuli_style()` (returns a context manager), `use_lazuli_style()` (mutates global rcParams), and private `_style_path()`, `_apply_axis_cosmetics(ax)`, `_prepare_ax(ax)`.

- [ ] **Step 1: Create the shipped style file**

Create `src/esc_etc/data/lazuli.mplstyle` with EXACTLY this content (verbatim canonical style, only the first comment line changed to note the source):

```
# lazuli.mplstyle — clean publication plotting style for the Lazuli ETCs.
# Canonical source: lazuli-transit/notebooks/lazuli.mplstyle (kept byte-identical).
#   import matplotlib.pyplot as plt; plt.style.use("lazuli.mplstyle")

# --- fonts (STIX serif, LaTeX-like) ---
mathtext.fontset:      stix
font.family:           STIXGeneral
axes.formatter.useoffset: False

# --- sizes ---
axes.labelsize:        13
axes.titlesize:        13
legend.fontsize:       10
figure.dpi:            150
savefig.dpi:           150
savefig.bbox:          tight

# --- ticks: inward, with minor ticks shown ---
xtick.direction:       in
ytick.direction:       in
xtick.minor.visible:   True
ytick.minor.visible:   True
xtick.top:             True
ytick.right:           True

# --- subtle grid ---
axes.grid:             True
grid.alpha:            0.3
grid.linewidth:        0.3

# --- lines & legend ---
lines.linewidth:       2.0
legend.frameon:        False

# --- qualitative palette (teal, red, amber, blue, green, dark-blue) ---
axes.prop_cycle: cycler('color', ['00798c', 'd1495b', 'edae49', '30638e', '66a182', '003d5b'])
```

- [ ] **Step 2: Add the package-data glob so the style ships in the wheel**

In `pyproject.toml`, find the `[tool.setuptools.package-data]` line:
```toml
"esc_etc" = ["support_data/**/*", "configs/**/*.toml"] # Edit the config_project part
```
Change it to add the style glob:
```toml
"esc_etc" = ["support_data/**/*", "configs/**/*.toml", "data/*.mplstyle"]
```

- [ ] **Step 3: Write the failing test**

```python
# tests/test_plotting_style.py
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import matplotlib.colors as mcolors

from esc_etc.plotting import (
    TEAL, RED, AMBER, BLUE, GREEN, DARKBLUE, LAZULI_COLORS,
    lazuli_style, use_lazuli_style, _style_path, _apply_axis_cosmetics,
)


def test_color_tokens_match_canonical_hex():
    assert TEAL == "#00798c"
    assert RED == "#d1495b"
    assert AMBER == "#edae49"
    assert BLUE == "#30638e"
    assert GREEN == "#66a182"
    assert DARKBLUE == "#003d5b"
    assert LAZULI_COLORS == [TEAL, RED, AMBER, BLUE, GREEN, DARKBLUE]


def test_style_file_is_shipped_and_resolvable():
    path = _style_path()
    assert str(path).endswith("data/lazuli.mplstyle")
    text = path.read_text()
    assert "axes.prop_cycle" in text
    assert "00798c" in text


def test_lazuli_style_context_does_not_mutate_global_rcparams():
    before = plt.rcParams["xtick.direction"]
    with lazuli_style():
        assert plt.rcParams["xtick.direction"] == "in"
    assert plt.rcParams["xtick.direction"] == before


def test_use_lazuli_style_mutates_global_rcparams():
    with plt.rc_context():  # isolates the global mutation to this block
        use_lazuli_style()
        assert plt.rcParams["xtick.direction"] == "in"


def test_apply_axis_cosmetics_sets_grid_and_inward_ticks():
    fig, ax = plt.subplots()
    _apply_axis_cosmetics(ax)
    assert ax.xaxis.get_gridlines()  # grid lines exist
    plt.close(fig)
```

- [ ] **Step 4: Run test to verify it fails**

Run: `pytest tests/test_plotting_style.py -v`
Expected: FAIL with `ModuleNotFoundError: No module named 'esc_etc.plotting'`

- [ ] **Step 5: Write the module foundation**

```python
# src/esc_etc/plotting.py
"""Lazuli-styled matplotlib plotting helpers for the ESC ETC.

Mirrors wcc-etc's plotting.py conventions: each helper takes the domain object
(Simulation/Coronagraph/Sensor/Scene) positionally OR explicit raw arrays as
keywords, accepts ax=None, applies the lazuli style via a context manager, and
returns (fig, ax). The style ships as data/lazuli.mplstyle (byte-identical to the
canonical lazuli-transit copy).
"""
import importlib.resources

import numpy as np
import matplotlib.pyplot as plt

# Lazuli qualitative palette (hex), in prop_cycle order.
TEAL = "#00798c"
RED = "#d1495b"
AMBER = "#edae49"
BLUE = "#30638e"
GREEN = "#66a182"
DARKBLUE = "#003d5b"
LAZULI_COLORS = [TEAL, RED, AMBER, BLUE, GREEN, DARKBLUE]


def _style_path():
    """Filesystem path to the shipped lazuli.mplstyle."""
    return importlib.resources.files("esc_etc") / "data" / "lazuli.mplstyle"


def lazuli_style():
    """Context manager applying the lazuli style without touching global rcParams.

    Usage: ``with lazuli_style(): ...``. Every helper wraps its drawing in this.
    """
    return plt.style.context(str(_style_path()))


def use_lazuli_style():
    """Apply the lazuli style to matplotlib's global rcParams (opt-in, mutates state)."""
    plt.style.use(str(_style_path()))


def _apply_axis_cosmetics(ax):
    """Inward minor+major ticks on all sides and a subtle grid.

    Applied to whatever axis a helper draws on so a user-supplied `ax` (whose
    rcParams were fixed at creation) still gets the lazuli look.
    """
    ax.minorticks_on()
    ax.tick_params(which="both", direction="in", top=True, right=True)
    ax.grid(True, alpha=0.3, linewidth=0.3)


def _prepare_ax(ax):
    """Return (fig, ax): create a new fig/ax if ax is None, else reuse the given ax."""
    if ax is None:
        fig, ax = plt.subplots()
    else:
        fig = ax.figure
    return fig, ax


def _require(value, name, alt):
    """Raise a clear ValueError when neither a domain object nor its arrays were given."""
    if value is None:
        raise ValueError(
            f"Provide either a domain object or {name!r} (and {alt}). Got neither."
        )
    return value
```

- [ ] **Step 6: Run test to verify it passes**

Run: `pytest tests/test_plotting_style.py -v`
Expected: PASS (5 passed)

- [ ] **Step 7: Commit**

```bash
git add src/esc_etc/data/lazuli.mplstyle src/esc_etc/plotting.py pyproject.toml tests/test_plotting_style.py
git commit -m "feat: add lazuli plotting style + style utilities"
```

---

### Task 2: Count-rate breakdown + SNR-vs-time helpers

**Files:**
- Modify: `src/esc_etc/plotting.py`
- Test: `tests/test_plotting_rates.py`

**Interfaces:**
- Consumes: `_prepare_ax`, `_apply_axis_cosmetics`, `lazuli_style`, `LAZULI_COLORS`, `_require` (Task 1); `CountRates` (`esc_etc.noise`); `Simulation.count_rate_components`, `Simulation.get_snr`/`.noise_model`/`.sensor`/`.coronagraph`.
- Produces: `plot_count_rates(sim=None, *, rates=None, sensor=None, ax=None, log=True) -> (fig, ax)`; `plot_snr_vs_time(sim=None, *, total_times=None, frame_time=None, snrs=None, ax=None) -> (fig, ax)`.

- [ ] **Step 1: Write the failing tests**

```python
# tests/test_plotting_rates.py
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import matplotlib.colors as mcolors
import numpy as np
import astropy.units as u
import pytest

from esc_etc.noise import CountRates
from esc_etc.plotting import plot_count_rates, plot_snr_vs_time, TEAL


class _Sensor:
    dark_current = 0.001 * u.electron / (u.s * u.pix)
    num_psf_pixels = 225.0 * u.pix


def _rates():
    e = u.electron / u.s
    return CountRates(source=0.9 * e, zodi=2.3e-4 * e, exozodi=1e-4 * e,
                      speckle=0.9 * e, host=9e7 * e)


def test_count_rates_raw_path_draws_five_bars():
    fig, ax = plot_count_rates(rates=_rates(), sensor=_Sensor())
    assert len(ax.patches) == 5
    assert ax.get_ylabel() != ""
    # first bar uses the lazuli TEAL
    assert ax.patches[0].get_facecolor() == mcolors.to_rgba(TEAL)
    assert ax.get_yscale() == "log"
    plt.close(fig)


def test_count_rates_requires_inputs():
    with pytest.raises(ValueError):
        plot_count_rates()  # no sim, no rates


def test_snr_vs_time_raw_path_plots_supplied_arrays():
    times = np.array([10.0, 100.0, 1000.0]) * u.s
    snrs = np.array([1.0, 5.0, 9.0])
    fig, ax = plot_snr_vs_time(total_times=times, snrs=snrs)
    line = ax.get_lines()[0]
    assert len(line.get_xdata()) == 3
    assert ax.get_xscale() == "log" and ax.get_yscale() == "log"
    assert ax.get_xlabel() != "" and ax.get_ylabel() != ""
    plt.close(fig)


def test_snr_vs_time_requires_inputs():
    with pytest.raises(ValueError):
        plot_snr_vs_time()  # no sim, no snrs
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `pytest tests/test_plotting_rates.py -v`
Expected: FAIL with `ImportError: cannot import name 'plot_count_rates'`

- [ ] **Step 3: Implement the two helpers (append to `src/esc_etc/plotting.py`)**

```python
import astropy.units as u  # add to the imports at the top of plotting.py


def plot_count_rates(sim=None, *, rates=None, sensor=None, ax=None, log=True):
    """Bar chart of count-rate contributors (e-/s): source, zodi, exozodi,
    speckle, and dark-current total (dark_current * num_psf_pixels).

    Pass a Simulation, or explicit `rates` (CountRates) + `sensor`. Returns (fig, ax).
    """
    if sim is not None:
        rates = sim.count_rate_components()
        sensor = sim.sensor
    _require(rates, "rates", "sensor")
    _require(sensor, "sensor", "rates")

    dark_total = (sensor.dark_current * sensor.num_psf_pixels)
    labels = ["Source", "Zodi", "Exozodi", "Speckle", "Dark"]
    values = np.array([
        rates.source.value, rates.zodi.value, rates.exozodi.value,
        rates.speckle.value, dark_total.value,
    ], dtype=float)
    if log:
        values = np.clip(values, 1e-30, None)

    with lazuli_style():
        fig, ax = _prepare_ax(ax)
        ax.bar(labels, values, color=LAZULI_COLORS[:len(labels)])
        if log:
            ax.set_yscale("log")
        ax.set_ylabel(r"Count rate [e$^-$/s]")
        ax.set_xlabel("Component")
        _apply_axis_cosmetics(ax)
        ax.grid(True, axis="y", alpha=0.3, linewidth=0.3)
    return fig, ax


def plot_snr_vs_time(sim=None, *, total_times=None, frame_time=None, snrs=None, ax=None):
    """SNR vs total integration time (log-log).

    Pass a Simulation (sweeps `total_times`, default logspace 10..1e5 s, computing
    SNR per point via the engine's noise_model with a single count-rate evaluation),
    or explicit `(total_times, snrs)`. `frame_time` defaults to 100 s. Returns (fig, ax).
    """
    if frame_time is None:
        frame_time = 100 * u.s
    if total_times is None and sim is not None:
        total_times = np.logspace(1, 5, 40) * u.s
    if snrs is None:
        _require(sim, "snrs", "total_times")
        rates = sim.count_rate_components()
        snrs = np.array([
            sim.noise_model.snr(rates, sim.sensor, sim.coronagraph, t, frame_time)["snr"]
            for t in total_times
        ], dtype=float)

    t_s = u.Quantity(total_times, u.s).value
    with lazuli_style():
        fig, ax = _prepare_ax(ax)
        ax.loglog(t_s, np.asarray(snrs, dtype=float), color=TEAL)
        ax.set_xlabel("Integration time [s]")
        ax.set_ylabel("SNR")
        _apply_axis_cosmetics(ax)
    return fig, ax
```

- [ ] **Step 4: Run tests to verify they pass**

Run: `pytest tests/test_plotting_rates.py -v`
Expected: PASS (4 passed)

- [ ] **Step 5: Commit**

```bash
git add src/esc_etc/plotting.py tests/test_plotting_rates.py
git commit -m "feat: add plot_count_rates and plot_snr_vs_time helpers"
```

---

### Task 3: Off-axis throughput, bandpass, and spectra helpers

**Files:**
- Modify: `src/esc_etc/plotting.py`
- Test: `tests/test_plotting_curves.py`

**Interfaces:**
- Consumes: `_prepare_ax`, `_apply_axis_cosmetics`, `lazuli_style`, `LAZULI_COLORS`, `TEAL`, `_require` (Task 1); `Coronagraph.off_axis_throughput`/`.separation`; `Sensor.bandpass`; `Scene`/`SceneElement.spectrum`.
- Produces: `plot_offaxis_throughput(coronagraph=None, *, separations=None, throughputs=None, ax=None, mark_separation=True) -> (fig, ax)`; `plot_bandpass(sensor=None, *, wavelength=None, throughput=None, ax=None) -> (fig, ax)`; `plot_spectra(scene=None, *, which=("star","planet","zodi"), ax=None) -> (fig, ax)`.

- [ ] **Step 1: Write the failing tests**

```python
# tests/test_plotting_curves.py
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np
import astropy.units as u
import pytest
from synphot import SourceSpectrum
from synphot.models import ConstFlux1D

from esc_etc.scene import Scene, SceneElement
from esc_etc.plotting import plot_offaxis_throughput, plot_bandpass, plot_spectra


def test_offaxis_throughput_raw_path():
    seps = np.linspace(0.1, 0.5, 20)
    tput = np.linspace(0.1, 0.6, 20)
    fig, ax = plot_offaxis_throughput(separations=seps, throughputs=tput,
                                      mark_separation=False)
    assert len(ax.get_lines()[0].get_xdata()) == 20
    assert ax.get_xlabel() != "" and ax.get_ylabel() != ""
    plt.close(fig)


def test_offaxis_throughput_requires_inputs():
    with pytest.raises(ValueError):
        plot_offaxis_throughput()


def test_bandpass_raw_path():
    wave = np.linspace(400, 800, 50)  # nm
    tput = np.exp(-((wave - 600) ** 2) / (2 * 30 ** 2))
    fig, ax = plot_bandpass(wavelength=wave, throughput=tput)
    assert len(ax.get_lines()[0].get_xdata()) == 50
    assert ax.get_xlabel() != "" and ax.get_ylabel() != ""
    plt.close(fig)


def test_bandpass_requires_inputs():
    with pytest.raises(ValueError):
        plot_bandpass()


def _toy_scene():
    flat = SourceSpectrum(ConstFlux1D, amplitude=0 * u.ABmag)
    star = SceneElement("star", flat, mag=0.0)
    planet = SceneElement("planet", flat, mag=0.0, deltamag=20.0)
    zodi = SceneElement("zodi", flat, mag=22.5)
    exozodi = SceneElement("exozodi", flat, mag=21.0)
    return Scene(star, planet, zodi, exozodi)


def test_spectra_draws_one_line_per_element():
    fig, ax = plot_spectra(_toy_scene(), which=("star", "planet", "zodi"))
    assert len(ax.get_lines()) == 3
    assert ax.get_legend() is not None
    plt.close(fig)


def test_spectra_requires_scene():
    with pytest.raises(ValueError):
        plot_spectra()
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `pytest tests/test_plotting_curves.py -v`
Expected: FAIL with `ImportError: cannot import name 'plot_offaxis_throughput'`

- [ ] **Step 3: Implement the three helpers (append to `src/esc_etc/plotting.py`)**

```python
def plot_offaxis_throughput(coronagraph=None, *, separations=None, throughputs=None,
                            ax=None, mark_separation=True):
    """Coronagraph off-axis (FPM) throughput vs planet separation (arcsec).

    Pass a Coronagraph, a Simulation (uses .coronagraph), or explicit
    (separations, throughputs). When `mark_separation`, draws a vertical marker at
    the coronagraph's current separation. Returns (fig, ax).
    """
    if coronagraph is not None and hasattr(coronagraph, "coronagraph"):
        coronagraph = coronagraph.coronagraph  # a Simulation was passed
    if throughputs is None:
        _require(coronagraph, "throughputs", "separations")
        if separations is None:
            separations = np.linspace(0.05, 0.6, 60)
        throughputs = np.array([coronagraph.off_axis_throughput(float(s))
                                for s in separations], dtype=float)

    with lazuli_style():
        fig, ax = _prepare_ax(ax)
        ax.plot(np.asarray(separations, dtype=float),
                np.asarray(throughputs, dtype=float), color=TEAL)
        if mark_separation and coronagraph is not None:
            ax.axvline(coronagraph.separation, color=RED, ls="--", lw=1.0,
                       label=f"separation = {coronagraph.separation} arcsec")
            ax.legend()
        ax.set_xlabel("Separation [arcsec]")
        ax.set_ylabel("Off-axis throughput")
        _apply_axis_cosmetics(ax)
    return fig, ax


def plot_bandpass(sensor=None, *, wavelength=None, throughput=None, ax=None):
    """Instrument bandpass throughput vs wavelength (nm).

    Pass a Sensor, a Simulation (uses .sensor), or explicit (wavelength, throughput).
    `wavelength` may be an astropy Quantity (converted to nm) or a plain array (nm).
    Returns (fig, ax).
    """
    if sensor is not None and hasattr(sensor, "sensor"):
        sensor = sensor.sensor  # a Simulation was passed
    if throughput is None:
        _require(sensor, "throughput", "wavelength")
        bp = sensor.bandpass
        wave_q = bp.waveset  # astropy Quantity (Angstrom)
        wavelength = wave_q.to(u.nm).value
        tput = bp(wave_q)
        throughput = np.asarray(getattr(tput, "value", tput), dtype=float)
    else:
        wavelength = (u.Quantity(wavelength).to(u.nm).value
                      if hasattr(wavelength, "unit") else np.asarray(wavelength, dtype=float))

    with lazuli_style():
        fig, ax = _prepare_ax(ax)
        ax.plot(np.asarray(wavelength, dtype=float),
                np.asarray(throughput, dtype=float), color=TEAL)
        ax.set_xlabel("Wavelength [nm]")
        ax.set_ylabel("Throughput")
        _apply_axis_cosmetics(ax)
    return fig, ax


def plot_spectra(scene=None, *, which=("star", "planet", "zodi"), ax=None):
    """Scene element spectra over 3000-9000 Angstrom.

    Pass a Scene or a Simulation (uses .scene). `which` names the elements to draw.
    Returns (fig, ax).
    """
    if scene is not None and hasattr(scene, "scene"):
        scene = scene.scene  # a Simulation was passed
    _require(scene, "scene", "which")

    wave = np.arange(3000, 9000, 5) * u.AA
    wave_nm = wave.to(u.nm).value
    with lazuli_style():
        fig, ax = _prepare_ax(ax)
        for i, name in enumerate(which):
            element = getattr(scene, name)
            flux = element.spectrum(wave)
            y = np.asarray(getattr(flux, "value", flux), dtype=float)
            ax.plot(wave_nm, y, color=LAZULI_COLORS[i % len(LAZULI_COLORS)], label=name)
        ax.set_xlabel("Wavelength [nm]")
        ax.set_ylabel("Flux [PHOTLAM]")
        ax.legend()
        _apply_axis_cosmetics(ax)
    return fig, ax
```

- [ ] **Step 4: Run tests to verify they pass**

Run: `pytest tests/test_plotting_curves.py -v`
Expected: PASS (6 passed)

- [ ] **Step 5: Commit**

```bash
git add src/esc_etc/plotting.py tests/test_plotting_curves.py
git commit -m "feat: add plot_offaxis_throughput, plot_bandpass, plot_spectra helpers"
```

---

### Task 4: Public exports, one integration test, and docs

**Files:**
- Modify: `src/esc_etc/__init__.py`
- Modify: `tests/test_public_api.py`
- Create: `tests/test_plotting_integration.py`
- Modify: `README.md`, `docs/ETC_Changelog.rst`

**Interfaces:**
- Consumes: all `plot_*` functions + style utilities (Tasks 1-3); `Simulation.from_default` (`esc_etc.simulation`).
- Produces: top-level imports for the plotting API.

- [ ] **Step 1: Write the failing export + integration tests**

Add to `tests/test_public_api.py` a new test (keep the existing one):
```python
def test_plotting_exports():
    import esc_etc
    for name in ["plot_count_rates", "plot_snr_vs_time", "plot_offaxis_throughput",
                 "plot_bandpass", "plot_spectra", "lazuli_style", "use_lazuli_style",
                 "LAZULI_COLORS", "TEAL", "RED", "AMBER", "BLUE", "GREEN", "DARKBLUE"]:
        assert hasattr(esc_etc, name), f"missing export: {name}"
```

Create `tests/test_plotting_integration.py`:
```python
# tests/test_plotting_integration.py
"""One slow, config-backed test exercising the Simulation domain-object path."""
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import astropy.units as u
import numpy as np
import pytest

pytest.importorskip("config_stp_esc")
pytest.importorskip("config_um")

from esc_etc.simulation import Simulation
from esc_etc.plotting import plot_count_rates, plot_snr_vs_time


def test_count_rates_and_snr_from_simulation():
    sim = Simulation.from_default(hoststarmag=-0.353, planetdeltamag=20.0,
                                  contrast=1e-8, ppgain=10, separation=0.4)
    fig, ax = plot_count_rates(sim)
    assert len(ax.patches) == 5
    plt.close(fig)

    # small sweep to keep it fast; count rates computed once internally
    fig, ax = plot_snr_vs_time(sim, total_times=np.array([100.0, 1000.0, 3600.0]) * u.s,
                               frame_time=100 * u.s)
    assert len(ax.get_lines()[0].get_xdata()) == 3
    plt.close(fig)
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `pytest tests/test_public_api.py::test_plotting_exports -v`
Expected: FAIL with `AssertionError: missing export: plot_count_rates`

- [ ] **Step 3: Add the exports to `src/esc_etc/__init__.py`**

After the existing component imports (and before/with the `__all__` assignment), add:
```python
from .plotting import (
    plot_count_rates, plot_snr_vs_time, plot_offaxis_throughput,
    plot_bandpass, plot_spectra, lazuli_style, use_lazuli_style,
    LAZULI_COLORS, TEAL, RED, AMBER, BLUE, GREEN, DARKBLUE,
)
```
And extend `__all__` with these names:
```python
    "plot_count_rates", "plot_snr_vs_time", "plot_offaxis_throughput",
    "plot_bandpass", "plot_spectra", "lazuli_style", "use_lazuli_style",
    "LAZULI_COLORS", "TEAL", "RED", "AMBER", "BLUE", "GREEN", "DARKBLUE",
```

- [ ] **Step 4: Run the export + integration tests**

Run: `pytest tests/test_public_api.py::test_plotting_exports tests/test_plotting_integration.py -v`
Expected: PASS (2 passed; the integration test is config-backed and slower — allow a long timeout).

- [ ] **Step 5: Update README and changelog**

In `README.md`, add a "Plotting" snippet:
```python
from esc_etc import Simulation, plot_count_rates, plot_snr_vs_time

sim = Simulation.from_default(separation=0.4, contrast=1e-8, ppgain=10)
fig, ax = plot_count_rates(sim)          # noise-contributor breakdown
fig, ax = plot_snr_vs_time(sim)          # SNR vs integration time (lazuli style)
```
Note: helpers use the packaged `lazuli.mplstyle`; call `use_lazuli_style()` to apply it globally to your own plots.

In `docs/ETC_Changelog.rst`, add an entry: new `esc_etc.plotting` module with five lazuli-styled helpers (count-rate breakdown, SNR-vs-time, off-axis throughput, bandpass, spectra), a packaged `lazuli.mplstyle`, and `lazuli_style()`/`use_lazuli_style()` + color tokens.

- [ ] **Step 6: Run the full suite**

Run: `pytest tests/ -q`
Expected: 0 failed; previously-green tests unchanged; the new plotting tests pass (the 6 xfails / 2 skips from prior work remain).

- [ ] **Step 7: Commit**

```bash
git add src/esc_etc/__init__.py tests/test_public_api.py tests/test_plotting_integration.py README.md docs/ETC_Changelog.rst
git commit -m "feat: export plotting API and document lazuli plotting helpers"
```

---

## Self-review

**Spec coverage:**
- Style file shipped + packaging → Task 1 (steps 1-2). Style utilities (`lazuli_style`, `use_lazuli_style`, tokens, `_apply_axis_cosmetics`) → Task 1. `plot_count_rates` + `plot_snr_vs_time` → Task 2. `plot_offaxis_throughput` + `plot_bandpass` + `plot_spectra` → Task 3. Error handling (`_require` ValueError; log-clip in count_rates) → Tasks 1-3. Testing (behavior not pixels, raw-array path, color assertion, no-global-mutation, exports) → Tasks 1-4. Exports + README + changelog → Task 4. Domain-object integration path → Task 4 integration test.
- YAGNI items (no Bokeh, no Simulation.plot_* methods, no 2D images, no palette edits) honored — none added.

**Placeholder scan:** No TBD/TODO; every code step shows complete, runnable code. README/changelog steps name exact content to add.

**Type consistency:** `lazuli_style()` (context manager), `use_lazuli_style()`, `_style_path()`, `_apply_axis_cosmetics(ax)`, `_prepare_ax(ax)`, `_require(value, name, alt)`, `LAZULI_COLORS`, and the six color tokens are defined in Task 1 and used with matching signatures in Tasks 2-4. All five `plot_*` signatures match between their definitions (Tasks 2-3) and the exports/integration usage (Task 4). `CountRates` fields (`source/zodi/exozodi/speckle/host`) and `Sensor.dark_current`/`num_psf_pixels`, `Coronagraph.off_axis_throughput`/`separation`, `Sensor.bandpass`, `SceneElement.spectrum` match the implemented OO modules.

**Risk note:** `importlib.resources.files("esc_etc")` resolves to the editable source tree (where `data/lazuli.mplstyle` lives), so the style loads under the required `pip install -e .`; the package-data glob (Task 1 step 2) covers the built-wheel case.
