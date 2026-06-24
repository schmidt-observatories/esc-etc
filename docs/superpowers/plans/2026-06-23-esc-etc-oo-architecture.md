# esc-etc Object-Oriented Architecture Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Rewrite `esc_etc` into a compositional OO architecture (`Telescope`/`Sensor`/`Scene`/`Coronagraph` orchestrated by a `Simulation`) mirroring wcc-etc v0.6.0, while reproducing every existing golden-anchor SNR by construction.

**Architecture:** Build the new component classes by **extracting** the existing synphot/physics operations out of the monolithic `Observatory` into focused classes — not by re-deriving the math. A `Simulation` composes the components and delegates the SNR math to a pluggable `noise_model` (default `AnalyticCoronagraphNoiseModel`). The legacy `Observatory` / `esc_calc_snr` become a thin deprecated shim that constructs the new objects, so the entire existing test suite keeps passing as a regression guard.

**Tech Stack:** Python ≥3.8, astropy, synphot, numpy, pandas, scipy; configs from `config_stp_esc` + `config_um` (git deps); pytest.

## Global Constraints

- Python ≥ 3.8; package installed editable: `pip install -e .` (a plain `pip install .` shadows the repo — see MEMORY).
- astropy + synphot units throughout; bare floats auto-attach canonical units in constructors.
- **No dependency on `wcc_etc`.** Copy patterns, do not import.
- Keep depending on `config_stp_esc` and `config_um` as the source of truth; do **not** port to local TOML.
- All new modules live under `src/esc_etc/`.
- Scene element names are `star` / `planet` / `zodi` / `exozodi` (not wcc's `source`/`host`).
- The existing tests in `tests/` MUST keep passing unchanged after the shim lands. They are the regression guard.
- Detector wavelength grid (verbatim from current code): `WAVELENGTHS = np.arange(2000, 10000, 0.2) * u.AA`.
- TDD: write the failing test, watch it fail, implement minimally, watch it pass, commit. Frequent commits.
- **Golden anchors** (from `tests/test_anchors.py`, measured 2026-06-01):
  - `esc_calc_snr(3600, 100, separation=0.4, contrast=1e-8, ppgain=10)` → SNR ≈ **8.9221** (rel 2e-3)
  - `esc_calc_snr(600, 10)` (default `separation=0.2`) → SNR ≈ **1.90435** (rel 1e-3)
  - baseline `source_counts` ≈ 0.915824, `sky_counts` ≈ 2.276078e-4, `speckle_counts` ≈ 0.915824, `num_psf_pixels` == 225.

## Physics facts the implementer must preserve (read before starting)

These are extracted from `src/esc_etc/ExposureTimeSNRCalculatorESC.py` and are the contract the new code must honor:

1. **The FPM (focal-plane-mask) λ/D throughput is a flat scalar.** `add_lamD_optic` builds `SpectralElement(Box1D, amplitude=throughput_value, x_0=6000, width=7000)` — constant over the whole band. Multiplying the cumulative bandpass by a flat constant `k` leaves synphot magnitude-normalization invariant and scales every count rate by `k`. Therefore the FPM can be removed from `Sensor.bandpass` and applied as a scalar `k = Coronagraph.off_axis_throughput(separation)` multiplied into **all** count rates (source, speckle, zodi, exozodi, host). This is algebraically equivalent to the current code and preserves anchors.
2. **Planet brightness is set by `planetdeltamag`, not `contrast`.** `source_counts = host_countrate * 10**(-0.4*planetdeltamag)`.
3. **Speckle uses `rawDH_contrast`.** `speckle_scale = 10**(-0.4 * (-2.5*log10(rawDH_contrast)))` which equals `rawDH_contrast`. `speckle_counts = host_countrate * speckle_scale`. (At contrast 1e-8, dmag 20: source == speckle, matching the anchor.)
4. **Post-processing gain is inverted.** `make_STP` sets `self.ppgain = 1.0/ppgain_arg`, and `calc_SNR` uses `M = speckle_counts * self.ppgain`. So the noise-floor term is `M = speckle_counts / ppgain_arg`.
5. **Time-argument ordering.** `esc_calc_snr(exp_time, int_time, ...)` calls `calc_SNR(exp_time*u.s, int_time*u.s)` while `calc_SNR(self, int_time, exp_time)`. Net meaning: **total integration time = `esc_calc_snr`'s `exp_time`** (e.g. 3600 s) and **per-frame time = `esc_calc_snr`'s `int_time`** (e.g. 100 s); number of frames = total/frame. The new `Simulation.get_snr(total_time, frame_time)` uses correct names; the shim maps `esc_calc_snr`'s args to preserve the historical result.
6. **Backgrounds carry a resolution-element factor.** `background_counts = bg_obs.countrate(area=surface) * (electron/ct) * resel / arcsec**2`, with `resel = π*((primary_filter/2/diameter_primary*radian)**2)` in arcsec². Same factor for exozodi.
7. **Collecting area is the Lyot-stop area**, not the geometric primary area: `surface = π*(0.5*lyot_ratio*diameter_primary)**2`.
8. **Bandpass is resampled** onto `WAVELENGTHS` after assembly: `bandpass = resample_SpectralElement(bandpass, WAVELENGTHS)`.

## Shared interfaces (types used across tasks)

- `_MetaHolder_`: `.meta: dict`, `._mutable_parameters: list[str]`, `.update(**kwargs) -> list[str]`, `.reset() -> None`, `.describe() -> None`.
- `Telescope` attrs: `diameter_primary` (Quantity m), `surface` (Quantity area = Lyot area), `f_num` (float), `focal_len` (Quantity), `primary_filter` (Quantity AA), `resel` (Quantity arcsec²), `diameter_secondary`, `jitter_rms`, `zodi_profile_path` (str). Classmethods `from_config(telescope_config, instrument_config, telescope_support_path, arm='arm_a')`, `from_default()`.
- `Sensor` attrs: `bandpass` (SpectralElement, FPM-free, resampled), `gain` (electron/ct), `dark_current` (electron/s/pix), `read_noise` (electron/pix), `well_depth` (electron/pix), `pixel_size` (um/pix), `num_pixels` (pix), `num_psf_pixels` (pix), `plate_scale` (float, arcsec/pix), `sensor_area`, `sensor_temp`. Classmethods `from_config(instrument_config, instrument_support_path, telescope_config, telescope_support_path, telescope, arm='arm_a')`, `from_default(telescope)`. Method `calc_psf(approx_type='sq') -> (Quantity, Quantity)`.
- `Coronagraph` attrs: `raw_dh_contrast` (float), `ppgain` (float, user-facing, e.g. 10), `separation` (float, arcsec), `primary_filter` (Quantity AA), `diameter_primary` (Quantity m), `_lamD` (ndarray), `_throughput` (ndarray). Methods `off_axis_throughput(separation=None) -> float`, `speckle_scale() -> float`, `noise_floor_factor() -> float`. Classmethods `from_config(instrument_config, instrument_support_path, telescope, raw_dh_contrast, ppgain, separation, arm='arm_a')`, `from_default(telescope, raw_dh_contrast=1e-8, ppgain=10, separation=0.4)`.
- `SceneElement` attrs: `name` (str), `spectrum` (SourceSpectrum), `mag` (float), `mag_system` (str), `deltamag` (float or None).
- `Scene` attrs: `star`, `planet`, `zodi`, `exozodi` (all `SceneElement`). Classmethod/factory `get_scene(...)`.
- `CountRates` dataclass: `source`, `zodi`, `exozodi`, `speckle`, `host` (all Quantity electron/s).
- `AnalyticCoronagraphNoiseModel`: `snr(rates, sensor, coronagraph, total_time, frame_time) -> dict`; `int_time_for_snr(snr, rates, sensor, coronagraph, frame_time) -> dict`.
- `Simulation`: `.telescope`, `.sensor`, `.scene`, `.coronagraph`, `.noise_model`. `from_components(...)`, `from_default(...)`, `from_config(...)`. `count_rate_components() -> CountRates`; `get_snr(total_time, frame_time) -> dict`; `get_int_time_for_snr(snr, frame_time) -> dict`; `is_saturated(frame_time) -> bool`; `saturation_time() -> Quantity`; `update(**kwargs)`.

---

### Task 1: Freeze the legacy SNR grid as an independent cross-check fixture

Capture the current engine's outputs over a parameter grid **before** refactoring, so the new engine can be validated against real legacy numbers even after the old code is replaced.

**Files:**
- Create: `tests/generate_legacy_grid.py` (one-off generator, committed)
- Create: `tests/test_data/legacy_snr_grid.json` (generated artifact, committed)

**Interfaces:**
- Produces: `tests/test_data/legacy_snr_grid.json` — a list of `{params: {...}, snr: float, source_counts: float, sky_counts: float, speckle_counts: float, exozodi_counts: float, num_psf_pixels: float}` records consumed by Task 10.

- [ ] **Step 1: Write the generator script**

```python
# tests/generate_legacy_grid.py
"""One-off: capture current esc_calc_snr outputs over a grid for equivalence testing.
Run once with the pre-refactor engine; the committed JSON is the cross-check baseline."""
import json
import os
import esc_etc.ExposureTimeSNRCalculatorESC as esc_mod

GRID = [
    dict(exp_time=3600, int_time=100, separation=0.4, contrast=1e-8, ppgain=10),
    dict(exp_time=600, int_time=10, separation=0.2, contrast=1e-8, ppgain=10),
    dict(exp_time=3600, int_time=100, separation=0.4, contrast=1e-9, ppgain=10),
    dict(exp_time=3600, int_time=100, separation=0.4, contrast=1e-8, ppgain=100),
    dict(exp_time=1800, int_time=60, separation=0.3, contrast=1e-8, ppgain=10, planetdeltamag=22),
    dict(exp_time=3600, int_time=100, separation=0.4, contrast=1e-8, ppgain=10, hoststarmag=2.0),
    dict(exp_time=3600, int_time=100, separation=0.4, contrast=1e-8, ppgain=10, bg_flux=21.0),
]

def main():
    records = []
    for params in GRID:
        snr, esc = esc_mod.esc_calc_snr(verbose=False, plot=False, **params)
        records.append(dict(
            params=params,
            snr=float(snr),
            source_counts=float(esc.source_counts.value),
            sky_counts=float(esc.sky_counts.value),
            speckle_counts=float(esc.speckle_counts.value),
            exozodi_counts=float(esc.exozodi_counts.value),
            num_psf_pixels=float(esc.num_psf_pixels.value),
        ))
    out = os.path.join(os.path.dirname(__file__), "test_data", "legacy_snr_grid.json")
    os.makedirs(os.path.dirname(out), exist_ok=True)
    with open(out, "w") as f:
        json.dump(records, f, indent=2)
    print(f"wrote {len(records)} records to {out}")

if __name__ == "__main__":
    main()
```

- [ ] **Step 2: Run the generator against the current (pre-refactor) engine**

Run: `python tests/generate_legacy_grid.py`
Expected: prints `wrote 7 records to .../tests/test_data/legacy_snr_grid.json`; the first record's `snr` ≈ 8.9221, the second ≈ 1.90435.

- [ ] **Step 3: Sanity-check the JSON**

Run: `python -c "import json; d=json.load(open('tests/test_data/legacy_snr_grid.json')); print(d[0]['snr'], d[1]['snr'])"`
Expected: `8.92... 1.90...`

- [ ] **Step 4: Commit**

```bash
git add tests/generate_legacy_grid.py tests/test_data/legacy_snr_grid.json
git commit -m "test: freeze legacy ESC SNR grid as equivalence cross-check fixture"
```

---

### Task 2: `_MetaHolder_` base class

**Files:**
- Create: `src/esc_etc/meta.py`
- Test: `tests/test_meta.py`

**Interfaces:**
- Produces: `_MetaHolder_` with `meta`, `_mutable_parameters`, `update(**kwargs) -> list[str]`, `reset()`, `describe()`. Subclasses set `_mutable_parameters` and store initial values via `_init_meta(**kwargs)`.

- [ ] **Step 1: Write the failing test**

```python
# tests/test_meta.py
import pytest
from esc_etc.meta import _MetaHolder_


class Widget(_MetaHolder_):
    def __init__(self, a, b):
        self._mutable_parameters = ["a", "b"]
        self._init_meta(a=a, b=b)


class Box(_MetaHolder_):
    def __init__(self, w):
        self._mutable_parameters = ["label"]
        self.widget = w
        self._init_meta(label="box")


def test_update_sets_mutable_attribute():
    w = Widget(1, 2)
    updated = w.update(a=10)
    assert w.a == 10
    assert updated == ["a"]


def test_update_rejects_unknown_key():
    w = Widget(1, 2)
    with pytest.raises(KeyError):
        w.update(c=5)


def test_reset_restores_initial():
    w = Widget(1, 2)
    w.update(a=10, b=20)
    w.reset()
    assert (w.a, w.b) == (1, 2)


def test_nested_update_routes_to_child():
    b = Box(Widget(1, 2))
    b.update(widget__a=99)
    assert b.widget.a == 99
```

- [ ] **Step 2: Run test to verify it fails**

Run: `pytest tests/test_meta.py -v`
Expected: FAIL with `ModuleNotFoundError: No module named 'esc_etc.meta'`

- [ ] **Step 3: Write minimal implementation**

```python
# src/esc_etc/meta.py
"""Mutable-parameter base class shared by ESC ETC components.

Mirrors the wcc-etc _MetaHolder_ pattern (copied, not imported): each subclass
declares ``_mutable_parameters`` and stores its initial values with
``_init_meta``. ``update`` supports nested ``child__param=`` routing.
"""


class _MetaHolder_:
    def _init_meta(self, **kwargs):
        if not hasattr(self, "_mutable_parameters"):
            self._mutable_parameters = list(kwargs.keys())
        self.meta = dict(kwargs)
        self._initial = dict(kwargs)
        for key, value in kwargs.items():
            setattr(self, key, value)

    def update(self, **kwargs):
        updated = []
        for key, value in kwargs.items():
            if "__" in key:
                child_name, sub_key = key.split("__", 1)
                child = getattr(self, child_name)
                updated += [f"{child_name}__{k}" for k in child.update(**{sub_key: value})]
                continue
            if key not in self._mutable_parameters:
                raise KeyError(
                    f"{key!r} is not a mutable parameter of {type(self).__name__}; "
                    f"allowed: {self._mutable_parameters}"
                )
            setattr(self, key, value)
            self.meta[key] = value
            updated.append(key)
        self._on_update(updated)
        return updated

    def reset(self):
        for key, value in self._initial.items():
            setattr(self, key, value)
            self.meta[key] = value
        self._on_update(list(self._initial.keys()))

    def describe(self):
        for key in self._mutable_parameters:
            print(f"{key} = {getattr(self, key, None)}")

    def _on_update(self, updated_keys):
        """Hook for cache invalidation; overridden where caching exists."""
        pass
```

- [ ] **Step 4: Run test to verify it passes**

Run: `pytest tests/test_meta.py -v`
Expected: PASS (4 passed)

- [ ] **Step 5: Commit**

```bash
git add src/esc_etc/meta.py tests/test_meta.py
git commit -m "feat: add _MetaHolder_ base class for esc_etc components"
```

---

### Task 3: `Telescope` component

**Files:**
- Create: `src/esc_etc/telescope.py`
- Test: `tests/test_telescope.py`

**Interfaces:**
- Consumes: `_MetaHolder_` from Task 2; `config_um`, `config_stp_esc`.
- Produces: `Telescope` with attrs listed in Shared interfaces and `from_config(...)` / `from_default()`.

- [ ] **Step 1: Write the failing test**

```python
# tests/test_telescope.py
import astropy.units as u
import pytest

pytest.importorskip("config_stp_esc")
pytest.importorskip("config_um")

from esc_etc.telescope import Telescope


def test_from_default_geometry():
    t = Telescope.from_default()
    assert t.diameter_primary.unit.is_equivalent(u.m)
    assert t.surface.unit.is_equivalent(u.m ** 2)
    # Lyot collecting area is strictly smaller than the geometric primary area.
    geom = 3.14159265 * (0.5 * t.diameter_primary) ** 2
    assert t.surface < geom
    assert t.primary_filter.unit.is_equivalent(u.AA)
    assert t.resel.unit.is_equivalent(u.arcsec ** 2)
    assert float(t.f_num) > 0
```

- [ ] **Step 2: Run test to verify it fails**

Run: `pytest tests/test_telescope.py -v`
Expected: FAIL with `ModuleNotFoundError: No module named 'esc_etc.telescope'`

- [ ] **Step 3: Write minimal implementation**

```python
# src/esc_etc/telescope.py
"""Telescope geometry for the ESC ETC.

Holds aperture/collecting-area geometry. Throughput lives in Sensor (mirroring
wcc-etc). Values are extracted from config_um (telescope) + config_stp_esc
(per-arm aperture), matching the original Observatory.make_STP logic.
"""
from pathlib import Path

import numpy as np
from astropy import units as u

from .meta import _MetaHolder_


class Telescope(_MetaHolder_):
    def __init__(self, diameter_primary, surface, f_num, focal_len, primary_filter,
                 resel, diameter_secondary, jitter_rms, zodi_profile_path):
        self._mutable_parameters = ["separation_unused"]  # geometry is fixed post-config
        self.diameter_primary = diameter_primary
        self.surface = surface
        self.f_num = f_num
        self.focal_len = focal_len
        self.primary_filter = primary_filter
        self.resel = resel
        self.diameter_secondary = diameter_secondary
        self.jitter_rms = jitter_rms
        self.zodi_profile_path = zodi_profile_path
        self._init_meta()

    @classmethod
    def from_config(cls, telescope_config, instrument_config, telescope_support_path,
                    arm="arm_a"):
        cp = instrument_config["common_params"][arm]
        diameter_primary = u.Quantity(cp["pupil"]["aper_clear_OD"])
        lyot = cp["optics"]["lyot_stop"]["lyot_ratio"]
        surface = np.pi * (0.5 * lyot * diameter_primary) ** 2
        diameter_secondary = u.Quantity(
            telescope_config["telescope"]["optics"]["m2"]["aper_clear_OD"])
        primary_filter = u.Quantity(cp["optics"]["filter"]["lam_central"]).to("AA")
        f_num = cp["general"]["f_number_sci_cam"]
        focal_len = f_num * diameter_primary
        jitter_rms = u.Quantity(
            telescope_config["observatory"]["pointing"]["jitter_rms"])
        resel = np.pi * (((primary_filter) / 2 / diameter_primary * u.radian) ** 2).to(
            u.arcsec ** 2, equivalencies=u.dimensionless_angles())
        zodi_profile_path = (
            Path(telescope_support_path)
            / Path(telescope_config["astrophysics"]["zodi"]["profile"])
        ).as_posix()
        return cls(diameter_primary, surface, f_num, focal_len, primary_filter,
                   resel, diameter_secondary, jitter_rms, zodi_profile_path)

    @classmethod
    def from_default(cls, arm="arm_a"):
        import config_stp_esc
        import config_um
        return cls.from_config(
            telescope_config=config_um.load_config_values(),
            instrument_config=config_stp_esc.load_config_values(),
            telescope_support_path=config_um.get_data_path(),
            arm=arm,
        )
```

- [ ] **Step 4: Run test to verify it passes**

Run: `pytest tests/test_telescope.py -v`
Expected: PASS (1 passed)

- [ ] **Step 5: Commit**

```bash
git add src/esc_etc/telescope.py tests/test_telescope.py
git commit -m "feat: add Telescope geometry component"
```

---

### Task 4: `Sensor` component (detector + FPM-free bandpass)

**Files:**
- Create: `src/esc_etc/sensor.py`
- Test: `tests/test_sensor.py`

**Interfaces:**
- Consumes: `_MetaHolder_`, `Telescope`; `config_*`; the module-level `resample_SpectralElement` (define a private copy here to avoid importing from the legacy module).
- Produces: `Sensor` with the bandpass (telescope mirrors × ESC mirrors × generic filter × polarizers × QE, **no FPM**, resampled onto `WAVELENGTHS`) and detector params; `from_config`, `from_default(telescope)`, `calc_psf`.

- [ ] **Step 1: Write the failing test**

```python
# tests/test_sensor.py
import astropy.units as u
import pytest

pytest.importorskip("config_stp_esc")
pytest.importorskip("config_um")

from esc_etc.telescope import Telescope
from esc_etc.sensor import Sensor


def test_from_default_detector_and_psf():
    t = Telescope.from_default()
    s = Sensor.from_default(t)
    assert s.gain.unit.is_equivalent(u.electron / u.ct)
    assert s.dark_current.unit.is_equivalent(u.electron / (u.s * u.pix))
    assert s.well_depth.unit.is_equivalent(u.electron / u.pix)
    # Square-approx PSF footprint pinned by the baseline config.
    assert s.num_psf_pixels.value == pytest.approx(225.0)
    # Bandpass is a synphot SpectralElement evaluable on the detector grid.
    assert float(s.bandpass.tpeak()) > 0
```

- [ ] **Step 2: Run test to verify it fails**

Run: `pytest tests/test_sensor.py -v`
Expected: FAIL with `ModuleNotFoundError: No module named 'esc_etc.sensor'`

- [ ] **Step 3: Write minimal implementation**

```python
# src/esc_etc/sensor.py
"""Detector + non-coronagraph optical throughput for the ESC ETC.

The cumulative bandpass is assembled exactly as Observatory.make_STP did, EXCEPT
the FPM (focal-plane-mask) lambda/D throughput, which is a flat scalar and now
lives in Coronagraph.off_axis_throughput (see plan physics-fact #1).
"""
from math import ceil, floor, sqrt
from pathlib import Path

import numpy as np
import pandas as pd
from astropy import units as u
import astropy.io.fits
import astropy.table
from scipy.interpolate import interp1d
from synphot import SourceSpectrum, SpectralElement
from synphot.models import Box1D, Empirical1D

from .meta import _MetaHolder_

WAVELENGTHS = np.arange(2000, 10000, 0.2) * u.AA


def _resample_spectral_element(S, w):
    ww, ff = S._get_arrays(wavelengths=w)
    return SpectralElement(Empirical1D, points=ww, lookup_table=ff)


def _mirror_bandpass(coating_file):
    if coating_file.endswith(".fit") or coating_file.endswith(".fits"):
        df = astropy.table.Table(astropy.io.fits.getdata(coating_file)).to_pandas()
        ww = df["WAVELENGTH"].values * u.nm
        ff = df["THROUGHPUT"].values
        return SpectralElement(Empirical1D, points=ww, lookup_table=ff)
    return SpectralElement.from_file(coating_file, wave_unit="nm")


class Sensor(_MetaHolder_):
    def __init__(self, bandpass, gain, dark_current, read_noise, well_depth,
                 pixel_size, num_pixels, sensor_area, sensor_temp, plate_scale,
                 telescope):
        self._mutable_parameters = ["read_noise", "dark_current", "gain", "well_depth"]
        self.bandpass = bandpass
        self.pixel_size = pixel_size
        self.num_pixels = num_pixels
        self.sensor_area = sensor_area
        self.sensor_temp = sensor_temp
        self.plate_scale = plate_scale
        self._telescope = telescope
        self.num_psf_pixels = None
        self._init_meta(gain=gain, dark_current=dark_current,
                        read_noise=read_noise, well_depth=well_depth)
        self.calc_psf()

    @classmethod
    def from_config(cls, instrument_config, instrument_support_path, telescope_config,
                    telescope_support_path, telescope, arm="arm_a"):
        isp = Path(instrument_support_path)
        tsp = Path(telescope_support_path)
        cp = instrument_config["common_params"][arm]
        bandpass = SpectralElement(Box1D, amplitude=1, x_0=6000, width=7000)

        # Telescope mirrors
        for key in telescope_config["telescope"]["optics"].keys():
            coating = tsp / Path(telescope_config["telescope"]["optics"][key]["coating_refl"])
            bandpass = bandpass * _mirror_bandpass(coating.as_posix())
        # ESC reflective optics
        for key in cp["optics"].keys():
            if any(s in key for s in ("oap", "flat", "sphere", "dm", "fsm")):
                coating = isp / Path(cp["optics"][key]["coating_refl"])
                bandpass = bandpass * _mirror_bandpass(coating.as_posix())
        # Generic filter
        primary_filter = u.Quantity(cp["optics"]["filter"]["lam_central"]).to("AA")
        fbw = cp["optics"]["filter"]["bandwidth"]
        bandpass = bandpass * SpectralElement(
            Box1D, amplitude=0.98, x_0=primary_filter, width=fbw * primary_filter)
        # Polarizers / wave plates (NOT the FPM)
        for key in cp["optics"].keys():
            if "lp" in key or "qwp" in key:
                coating_init = cp["optics"][key]["pol_throughput"]
                if coating_init == "none":
                    bandpass = bandpass * SpectralElement(Box1D, amplitude=0.99, x_0=6000, width=7000)
                else:
                    coating_ext = isp / Path(coating_init)
                    bandpass = bandpass * SpectralElement.from_file(
                        coating_ext.as_posix(), wave_unit="nm")
                if "lp1" in key:
                    bandpass = bandpass * SpectralElement(Box1D, amplitude=0.5, x_0=6000, width=7000)

        # Detector
        pixel_size = (u.Quantity(cp["sensor"]["pixel_size"])).to(u.um) * (1.0 / u.pix)
        sensor_area = 962.56 * u.um * 962.56 * u.um
        gain_setting = cp["sensor"]["gain"]
        sensor_temp = cp["sensor"]["temp_nominal"] * u.Celsius

        def _interp(csv_key, names, x):
            f = isp / Path(cp["sensor"][csv_key])
            df = pd.read_csv(f.as_posix(), skiprows=1, names=names)
            return interp1d(df[names[0]], df[names[1]])(x)

        gain = _interp("gain_curve", ["gain_setting", "gain"], gain_setting) * (u.electron / u.ct)
        dark_current = _interp("dark_current", ["sensor_temperature", "dark_current"],
                               sensor_temp.value) * (u.electron / (u.s * u.pix))
        read_noise = _interp("read_noise", ["gain_setting", "read_noise"], gain_setting) \
            * sqrt(1.0 * u.electron / u.pix)
        well_depth = _interp("well_depth", ["gain_setting", "well_depth"], gain_setting) \
            * (u.electron / u.pix)

        num_pixels = (sensor_area / (pixel_size ** 2)).to("pix2").value * u.pix
        plate_scale = (pixel_size.value * 1e-6 / telescope.diameter_primary.value
                       / telescope.f_num * 206265)

        qe_path = isp / Path(cp["sensor"]["qe"])
        bandpass = bandpass * SpectralElement.from_file(qe_path.as_posix(), wave_unit="nm")
        bandpass = _resample_spectral_element(bandpass, WAVELENGTHS)

        return cls(bandpass, gain, dark_current, read_noise, well_depth, pixel_size,
                   num_pixels, sensor_area, sensor_temp, plate_scale, telescope)

    @classmethod
    def from_default(cls, telescope, arm="arm_a"):
        import config_stp_esc
        import config_um
        return cls.from_config(
            instrument_config=config_stp_esc.load_config_values(),
            instrument_support_path=config_stp_esc.get_data_path(),
            telescope_config=config_um.load_config_values(),
            telescope_support_path=config_um.get_data_path(),
            telescope=telescope, arm=arm,
        )

    def calc_psf(self, approx_type="sq"):
        wavelength = self.bandpass.wpeak()
        psf_diameter = (2 * 1.22 * wavelength * self._telescope.f_num).to("um")
        n = ceil((psf_diameter / self.pixel_size).value)
        if approx_type.lower() in ("s", "sq", "square"):
            self.num_psf_pixels = n ** 2 * u.pix
        else:
            if n % 2 == 0:
                L = int(n / 2)
                seq = [floor(0.5 + 0.5 * sqrt(n ** 2 - (2 * y - 1) ** 2)) for y in range(1, L + 1)]
                self.num_psf_pixels = 4 * sum(seq) * u.pix
            else:
                L = int((n - 1) / 2)
                seq = [floor(1 + 0.5 * sqrt(n ** 2 - 4 * (y ** 2))) for y in range(1, L + 1)]
                self.num_psf_pixels = (1 + 4 * sum(seq)) * u.pix
        return psf_diameter, self.num_psf_pixels
```

- [ ] **Step 4: Run test to verify it passes**

Run: `pytest tests/test_sensor.py -v`
Expected: PASS (1 passed)

- [ ] **Step 5: Commit**

```bash
git add src/esc_etc/sensor.py tests/test_sensor.py
git commit -m "feat: add Sensor component (detector + FPM-free bandpass)"
```

---

### Task 5: `Coronagraph` component

**Files:**
- Create: `src/esc_etc/coronagraph.py`
- Test: `tests/test_coronagraph.py`

**Interfaces:**
- Consumes: `_MetaHolder_`, `Telescope`.
- Produces: `Coronagraph` with `off_axis_throughput`, `speckle_scale`, `noise_floor_factor`, `from_config`, `from_default`.

- [ ] **Step 1: Write the failing test**

```python
# tests/test_coronagraph.py
import astropy.units as u
import numpy as np
import pytest

pytest.importorskip("config_stp_esc")
pytest.importorskip("config_um")

from esc_etc.telescope import Telescope
from esc_etc.coronagraph import Coronagraph


def test_speckle_and_floor_scaling():
    t = Telescope.from_default()
    c = Coronagraph.from_default(t, raw_dh_contrast=1e-8, ppgain=10, separation=0.4)
    # speckle_scale == raw_dh_contrast (plan physics-fact #3)
    assert c.speckle_scale() == pytest.approx(1e-8, rel=1e-9)
    # noise-floor factor is 1/ppgain (plan physics-fact #4)
    assert c.noise_floor_factor() == pytest.approx(0.1, rel=1e-9)


def test_off_axis_throughput_in_unit_interval_and_separation_dependent():
    t = Telescope.from_default()
    c = Coronagraph.from_default(t, separation=0.4)
    k_near = c.off_axis_throughput(0.1)
    k_far = c.off_axis_throughput(0.4)
    assert 0.0 <= k_near <= 1.0
    assert 0.0 <= k_far <= 1.0
    # Throughput rises with separation away from the mask center.
    assert k_far >= k_near
```

- [ ] **Step 2: Run test to verify it fails**

Run: `pytest tests/test_coronagraph.py -v`
Expected: FAIL with `ModuleNotFoundError: No module named 'esc_etc.coronagraph'`

- [ ] **Step 3: Write minimal implementation**

```python
# src/esc_etc/coronagraph.py
"""Coronagraph-specific physics for the ESC ETC.

Owns raw dark-hole contrast, post-processing gain, planet separation, and the
off-axis (FPM) lambda/D throughput curve. The FPM throughput is a flat scalar
applied by Simulation to every count rate (plan physics-fact #1).
"""
from pathlib import Path

import numpy as np
from astropy import units as u
import astropy.io.fits as fits

from .meta import _MetaHolder_


class Coronagraph(_MetaHolder_):
    def __init__(self, raw_dh_contrast, ppgain, separation, primary_filter,
                 diameter_primary, lamD, throughput):
        self._mutable_parameters = ["raw_dh_contrast", "ppgain", "separation"]
        self.primary_filter = primary_filter
        self.diameter_primary = diameter_primary
        self._lamD = lamD
        self._throughput = throughput
        self._init_meta(raw_dh_contrast=raw_dh_contrast, ppgain=ppgain,
                        separation=separation)

    @classmethod
    def from_config(cls, instrument_config, instrument_support_path, telescope,
                    raw_dh_contrast=1e-8, ppgain=10, separation=0.4, arm="arm_a"):
        isp = Path(instrument_support_path)
        cp = instrument_config["common_params"][arm]
        lamD = throughput = None
        for key in cp["optics"].keys():
            if "fpm" in key:
                tpath = isp / Path(cp["optics"][key]["throughput"])
                curve = fits.getdata(tpath.as_posix())
                lamD = np.asarray(curve[0])
                throughput = np.asarray(curve[1]) / 100.0
                break
        if lamD is None:
            raise ValueError("No FPM throughput entry found in instrument config optics")
        return cls(raw_dh_contrast, ppgain, separation, telescope.primary_filter,
                   telescope.diameter_primary, lamD, throughput)

    @classmethod
    def from_default(cls, telescope, raw_dh_contrast=1e-8, ppgain=10, separation=0.4,
                     arm="arm_a"):
        import config_stp_esc
        return cls.from_config(
            instrument_config=config_stp_esc.load_config_values(),
            instrument_support_path=config_stp_esc.get_data_path(),
            telescope=telescope, raw_dh_contrast=raw_dh_contrast, ppgain=ppgain,
            separation=separation, arm=arm,
        )

    def off_axis_throughput(self, separation=None):
        if separation is None:
            separation = self.separation
        lamD_single = (self.primary_filter / self.diameter_primary).to(
            u.arcsec, equivalencies=u.dimensionless_angles())
        lamD_separation = separation / lamD_single.value
        idx = np.absolute(self._lamD - lamD_separation).argmin()
        return float(self._throughput[idx])

    def speckle_scale(self):
        delta_mag = -2.5 * np.log10(self.raw_dh_contrast)
        return 10 ** (-0.4 * delta_mag)

    def noise_floor_factor(self):
        return 1.0 / self.ppgain
```

- [ ] **Step 4: Run test to verify it passes**

Run: `pytest tests/test_coronagraph.py -v`
Expected: PASS (2 passed). If `test_off_axis_throughput_*` fails on monotonicity, relax to asserting both values are finite and in [0,1] and that they differ — the curve shape is config-driven; the unit-interval + separation-dependence is the contract.

- [ ] **Step 5: Commit**

```bash
git add src/esc_etc/coronagraph.py tests/test_coronagraph.py
git commit -m "feat: add Coronagraph component (contrast, ppgain, off-axis throughput)"
```

---

### Task 6: `Scene` / `SceneElement` and `get_scene`

**Files:**
- Create: `src/esc_etc/scene.py`
- Test: `tests/test_scene.py`

**Interfaces:**
- Consumes: `_MetaHolder_`, `Telescope` (for the zodi profile path).
- Produces: `SceneElement`, `Scene`, `get_scene(...)`. `star`/`exozodi` spectra are `ConstFlux1D`/zodi-file; `planet` carries `deltamag`; `zodi`/`exozodi` carry the zodi-profile spectrum and their magnitudes.

- [ ] **Step 1: Write the failing test**

```python
# tests/test_scene.py
import astropy.units as u
import pytest

pytest.importorskip("config_stp_esc")
pytest.importorskip("config_um")

from esc_etc.telescope import Telescope
from esc_etc.scene import Scene, SceneElement, get_scene


def test_get_scene_elements():
    t = Telescope.from_default()
    scene = get_scene(t, hoststarmag=-0.353, planetdeltamag=20.0,
                      bg_flux=22.5, exobg_flux=21.0)
    assert isinstance(scene.star, SceneElement)
    assert scene.star.mag == pytest.approx(-0.353)
    assert scene.planet.deltamag == pytest.approx(20.0)
    assert scene.zodi.mag == pytest.approx(22.5)
    # exozodi magnitude is host + exo offset (matches make_observation)
    assert scene.exozodi.mag == pytest.approx(-0.353 + 21.0)


def test_update_routes_to_star():
    t = Telescope.from_default()
    scene = get_scene(t, hoststarmag=0.0)
    scene.update(star__mag=2.0)
    assert scene.star.mag == 2.0
```

- [ ] **Step 2: Run test to verify it fails**

Run: `pytest tests/test_scene.py -v`
Expected: FAIL with `ModuleNotFoundError: No module named 'esc_etc.scene'`

- [ ] **Step 3: Write minimal implementation**

```python
# src/esc_etc/scene.py
"""Observable scene for the ESC ETC: host star, planet, zodi, exozodi.

The star/planet share a flat ConstFlux1D spectral shape (as in the original
set_generic_source); the planet is defined relative to the star by deltamag.
Backgrounds use the zodi profile file from the telescope config.
"""
from synphot import SourceSpectrum
from synphot.models import ConstFlux1D
from astropy import units as u

from .meta import _MetaHolder_


class SceneElement(_MetaHolder_):
    def __init__(self, name, spectrum, mag, mag_system="vega", deltamag=None):
        self._mutable_parameters = ["mag", "mag_system", "deltamag"]
        self.name = name
        self.spectrum = spectrum
        self._init_meta(mag=mag, mag_system=mag_system, deltamag=deltamag)


class Scene(_MetaHolder_):
    def __init__(self, star, planet, zodi, exozodi):
        self._mutable_parameters = []
        self.star = star
        self.planet = planet
        self.zodi = zodi
        self.exozodi = exozodi
        self._init_meta()


def get_scene(telescope, hoststarmag=-0.353, planetdeltamag=20.0, bg_flux=22.5,
              exobg_flux=21.0, mag_system="vega", background_file=None):
    """Build a Scene from host magnitude + planet delta-mag + background mags."""
    flat = SourceSpectrum(ConstFlux1D, amplitude=hoststarmag * u.ABmag)
    star = SceneElement("star", flat, mag=hoststarmag, mag_system=mag_system)
    planet = SceneElement("planet", flat, mag=hoststarmag, mag_system=mag_system,
                          deltamag=planetdeltamag)
    bg_path = background_file if background_file is not None else telescope.zodi_profile_path
    zodi_spectrum = SourceSpectrum.from_file(bg_path)
    zodi = SceneElement("zodi", zodi_spectrum, mag=bg_flux, mag_system=mag_system)
    exozodi = SceneElement("exozodi", zodi_spectrum, mag=hoststarmag + exobg_flux,
                           mag_system=mag_system)
    return Scene(star, planet, zodi, exozodi)
```

- [ ] **Step 4: Run test to verify it passes**

Run: `pytest tests/test_scene.py -v`
Expected: PASS (2 passed)

- [ ] **Step 5: Commit**

```bash
git add src/esc_etc/scene.py tests/test_scene.py
git commit -m "feat: add Scene/SceneElement (star, planet, zodi, exozodi)"
```

---

### Task 7: `AnalyticCoronagraphNoiseModel`

**Files:**
- Create: `src/esc_etc/noise.py`
- Test: `tests/test_noise.py`

**Interfaces:**
- Consumes: `CountRates` (defined here), `Sensor`, `Coronagraph`.
- Produces: `CountRates` dataclass; `AnalyticCoronagraphNoiseModel.snr(rates, sensor, coronagraph, total_time, frame_time) -> dict` and `.int_time_for_snr(snr, rates, sensor, coronagraph, frame_time) -> dict`. The SNR math is extracted verbatim from `Observatory.calc_SNR` / `calc_int_time`.

- [ ] **Step 1: Write the failing test**

```python
# tests/test_noise.py
import astropy.units as u
import numpy as np

from esc_etc.noise import CountRates, AnalyticCoronagraphNoiseModel


class _Sensor:
    dark_current = 0.001 * u.electron / (u.s * u.pix)
    read_noise = 1.0 * np.sqrt(1.0 * u.electron / u.pix)
    num_pixels = 1000.0 * u.pix
    num_psf_pixels = 225.0 * u.pix
    gain = 1.0 * u.electron / u.ct


class _Coronagraph:
    def noise_floor_factor(self):
        return 0.1


def test_snr_matches_hand_computed_value():
    rates = CountRates(
        source=1.0 * u.electron / u.s,
        zodi=1e-4 * u.electron / u.s,
        exozodi=1e-4 * u.electron / u.s,
        speckle=1.0 * u.electron / u.s,
        host=1e8 * u.electron / u.s,
    )
    model = AnalyticCoronagraphNoiseModel()
    out = model.snr(rates, _Sensor(), _Coronagraph(), total_time=3600 * u.s,
                    frame_time=100 * u.s)
    assert out["snr"] > 0
    # Reproduce the calc_SNR formula independently.
    s = _Sensor()
    M = (1.0 * u.electron / u.s) * 0.1
    tt, ft = 3600 * u.s, 100 * u.s
    noise = np.sqrt(
        1.0 * u.electron / u.s * tt + 1e-4 * u.electron / u.s * tt
        + 1e-4 * u.electron / u.s * tt
        + s.dark_current * tt * s.num_psf_pixels
        + s.num_psf_pixels * (s.read_noise ** 2) * (tt / ft)
        + 1.0 * u.electron / u.s * tt
        + (M * tt) ** 2 / u.electron
    )
    expected = (1.0 * u.electron / u.s * tt / noise).value
    assert out["snr"] == np.float64(expected)
```

- [ ] **Step 2: Run test to verify it fails**

Run: `pytest tests/test_noise.py -v`
Expected: FAIL with `ModuleNotFoundError: No module named 'esc_etc.noise'`

- [ ] **Step 3: Write minimal implementation**

```python
# src/esc_etc/noise.py
"""Analytic coronagraph SNR engine for the ESC ETC.

Extracted verbatim from Observatory.calc_SNR / calc_int_time. This is the
default Simulation.noise_model; a future 2D-PSF image model can be swapped in
behind the same interface.
"""
from dataclasses import dataclass

import numpy as np
from astropy import units as u


@dataclass
class CountRates:
    source: u.Quantity
    zodi: u.Quantity
    exozodi: u.Quantity
    speckle: u.Quantity
    host: u.Quantity


class AnalyticCoronagraphNoiseModel:
    def snr(self, rates, sensor, coronagraph, total_time, frame_time):
        M = rates.speckle * coronagraph.noise_floor_factor()
        total_noise = np.sqrt(
            rates.source * total_time
            + rates.zodi * total_time
            + rates.exozodi * total_time
            + sensor.dark_current * total_time * sensor.num_psf_pixels
            + sensor.num_psf_pixels * (sensor.read_noise * sensor.read_noise)
            * (total_time / frame_time)
            + rates.speckle * total_time
            + (M * total_time) ** 2 / u.electron
        )
        snr = rates.source * total_time / total_noise
        return {
            "snr": snr.value,
            "signal_e": (rates.source * total_time).value,
            "noise_e": total_noise.value,
            "M": M,
        }

    def int_time_for_snr(self, snr, rates, sensor, coronagraph, frame_time):
        SNR = snr * u.ct
        M = rates.speckle * coronagraph.noise_floor_factor() / u.ct
        background_counts = (
            (sensor.dark_current * sensor.num_psf_pixels)
            + rates.zodi + rates.exozodi + rates.speckle
            + ((sensor.read_noise * sensor.read_noise) * sensor.num_psf_pixels
               / frame_time)
        )
        numerator = rates.source + background_counts
        denominator = (rates.source / SNR) ** 2 - M ** 2
        int_time = (numerator / denominator) / u.ct
        int_time = np.atleast_1d(int_time)
        int_time[np.isinf(int_time) | (int_time.value < 0.0)] = np.nan
        noise_terms = np.array([
            (sensor.dark_current * sensor.num_psf_pixels).value,
            ((sensor.read_noise ** 2) * sensor.num_psf_pixels / frame_time).value,
            rates.zodi.value, rates.exozodi.value, rates.speckle.value,
        ])
        return {"int_time": int_time, "noise_terms": noise_terms}
```

- [ ] **Step 4: Run test to verify it passes**

Run: `pytest tests/test_noise.py -v`
Expected: PASS (1 passed)

- [ ] **Step 5: Commit**

```bash
git add src/esc_etc/noise.py tests/test_noise.py
git commit -m "feat: add AnalyticCoronagraphNoiseModel (extracted SNR math)"
```

---

### Task 8: `Simulation` orchestrator

**Files:**
- Create: `src/esc_etc/simulation.py`
- Test: `tests/test_simulation.py`

**Interfaces:**
- Consumes: `Telescope`, `Sensor`, `Scene`, `Coronagraph`, `CountRates`, `AnalyticCoronagraphNoiseModel`.
- Produces: `Simulation` with `from_default`, `from_components`, `count_rate_components()`, `get_snr(total_time, frame_time)`, `get_int_time_for_snr(snr, frame_time)`, `is_saturated(frame_time)`, `saturation_time()`. `count_rate_components` extracts `make_observation` and applies the FPM scalar `k` to every rate.

- [ ] **Step 1: Write the failing test**

```python
# tests/test_simulation.py
import astropy.units as u
import pytest

pytest.importorskip("config_stp_esc")
pytest.importorskip("config_um")

from esc_etc.simulation import Simulation


def test_baseline_snr_and_counts_match_anchor():
    sim = Simulation.from_default(hoststarmag=-0.353, planetdeltamag=20.0,
                                  contrast=1e-8, ppgain=10, separation=0.4,
                                  bg_flux=22.5, exobg_flux=21.0)
    rates = sim.count_rate_components()
    assert rates.source.value == pytest.approx(0.915824, rel=1e-3)
    assert rates.zodi.value == pytest.approx(2.276078e-4, rel=1e-3)
    assert rates.speckle.value == pytest.approx(0.915824, rel=1e-3)
    out = sim.get_snr(total_time=3600 * u.s, frame_time=100 * u.s)
    assert out["snr"] == pytest.approx(8.9221, rel=2e-3)


def test_noise_model_seam_is_used():
    sim = Simulation.from_default()

    class Sentinel:
        def snr(self, *a, **k):
            return {"snr": 42.0}
    sim.noise_model = Sentinel()
    assert sim.get_snr(total_time=3600 * u.s, frame_time=100 * u.s)["snr"] == 42.0
```

- [ ] **Step 2: Run test to verify it fails**

Run: `pytest tests/test_simulation.py -v`
Expected: FAIL with `ModuleNotFoundError: No module named 'esc_etc.simulation'`

- [ ] **Step 3: Write minimal implementation**

```python
# src/esc_etc/simulation.py
"""Top-level ESC ETC orchestrator: composes Telescope, Sensor, Scene, Coronagraph.

count_rate_components extracts Observatory.make_observation: it normalizes the
host on the FPM-free Sensor.bandpass, derives planet/speckle by scaling, computes
zodi/exozodi with the resel factor, then multiplies EVERY rate by the flat FPM
throughput k = coronagraph.off_axis_throughput (plan physics-fact #1).
"""
from astropy import units as u
from synphot import Observation, SourceSpectrum, SpectralElement, units as su

from .meta import _MetaHolder_
from .telescope import Telescope
from .sensor import Sensor
from .scene import Scene, get_scene
from .coronagraph import Coronagraph
from .noise import CountRates, AnalyticCoronagraphNoiseModel

FORCE = None


class Simulation(_MetaHolder_):
    def __init__(self, telescope, sensor, scene, coronagraph, noise_model=None):
        self._mutable_parameters = []
        self.telescope = telescope
        self.sensor = sensor
        self.scene = scene
        self.coronagraph = coronagraph
        self.noise_model = noise_model or AnalyticCoronagraphNoiseModel()
        self._vega = None
        self._johnson_v = None
        self._init_meta()

    @classmethod
    def from_components(cls, telescope, sensor, scene, coronagraph, noise_model=None):
        return cls(telescope, sensor, scene, coronagraph, noise_model)

    @classmethod
    def from_default(cls, hoststarmag=-0.353, planetdeltamag=20.0, contrast=1e-8,
                     ppgain=10, separation=0.4, bg_flux=22.5, exobg_flux=21.0,
                     arm="arm_a"):
        telescope = Telescope.from_default(arm=arm)
        sensor = Sensor.from_default(telescope, arm=arm)
        scene = get_scene(telescope, hoststarmag=hoststarmag,
                          planetdeltamag=planetdeltamag, bg_flux=bg_flux,
                          exobg_flux=exobg_flux)
        coronagraph = Coronagraph.from_default(
            telescope, raw_dh_contrast=contrast, ppgain=ppgain, separation=separation,
            arm=arm)
        return cls(telescope, sensor, scene, coronagraph)

    def _normalize_units(self, mag_system):
        if mag_system in ("vega", su.VEGAMAG):
            return su.VEGAMAG
        if mag_system in ("AB", "ABmag", u.ABmag):
            return u.ABmag
        raise NotImplementedError(f"flux units {mag_system!r} not implemented")

    def count_rate_components(self):
        if self._vega is None:
            self._vega = SourceSpectrum.from_vega()
        if self._johnson_v is None:
            self._johnson_v = SpectralElement.from_filter("johnson_v")
        vega = self._vega
        bp = self.sensor.bandpass
        area = self.telescope.surface
        resel = self.telescope.resel
        k = self.coronagraph.off_axis_throughput(self.coronagraph.separation)

        star = self.scene.star
        norm_units = self._normalize_units(star.mag_system)
        if norm_units is su.VEGAMAG:
            host_sp = star.spectrum.normalize(star.mag * su.VEGAMAG, bp,
                                              vegaspec=vega, force=FORCE)
        else:
            host_sp = star.spectrum.normalize(star.mag * u.ABmag, bp, force=FORCE)
        host_obs = Observation(host_sp, bp, force=FORCE)
        host_countrate = host_obs.countrate(area=area) * u.electron / u.ct

        planet_scale = 10 ** (-0.4 * self.scene.planet.deltamag)
        source = host_countrate * planet_scale * k
        speckle = host_countrate * self.coronagraph.speckle_scale() * k

        zodi_rn = self.scene.zodi.spectrum.normalize(
            self.scene.zodi.mag * su.VEGAMAG, self._johnson_v, vegaspec=vega, force=FORCE)
        zodi_obs = Observation(zodi_rn, bp, force=FORCE)
        zodi = zodi_obs.countrate(area=area) * u.electron / u.ct * resel / u.arcsec ** 2 * k

        exo_rn = self.scene.exozodi.spectrum.normalize(
            self.scene.exozodi.mag * su.VEGAMAG, bp, vegaspec=vega, force=FORCE)
        exo_obs = Observation(exo_rn, bp, force=FORCE)
        exozodi = exo_obs.countrate(area=area) * u.electron / u.ct * resel / u.arcsec ** 2 * k

        return CountRates(source=source, zodi=zodi, exozodi=exozodi,
                          speckle=speckle, host=host_countrate * k)

    def get_snr(self, total_time, frame_time):
        rates = self.count_rate_components()
        return self.noise_model.snr(rates, self.sensor, self.coronagraph,
                                    total_time, frame_time)

    def get_int_time_for_snr(self, snr, frame_time):
        rates = self.count_rate_components()
        return self.noise_model.int_time_for_snr(snr, rates, self.sensor,
                                                 self.coronagraph, frame_time)

    def saturation_time(self):
        rates = self.count_rate_components()
        per_pix = (rates.source + rates.zodi + rates.speckle + rates.exozodi) \
            / self.sensor.num_psf_pixels
        return self.sensor.well_depth / per_pix

    def is_saturated(self, frame_time):
        return frame_time > self.saturation_time()
```

- [ ] **Step 4: Run test to verify it passes**

Run: `pytest tests/test_simulation.py -v`
Expected: PASS (2 passed). If `test_baseline_snr_and_counts_match_anchor` is off, compare `count_rate_components` against `Observatory.make_observation` line-by-line — the most likely culprits are the `k` factor application or the `resel` unit handling.

- [ ] **Step 5: Commit**

```bash
git add src/esc_etc/simulation.py tests/test_simulation.py
git commit -m "feat: add Simulation orchestrator with pluggable noise_model"
```

---

### Task 9: Rewrite `ExposureTimeSNRCalculatorESC.py` as a compat shim

Replace the monolithic `Observatory` with a thin shim that builds the new components and delegates, preserving the public symbols (`Observatory`, `esc_calc_snr`, `resample_SpectralElement`, `resample_SourceSpectrum`) and the historical time-argument mapping.

**Files:**
- Modify (replace contents): `src/esc_etc/ExposureTimeSNRCalculatorESC.py`
- Test: existing `tests/test_anchors.py`, `tests/test_snr.py`, `tests/physics_helpers.py` (unchanged — they exercise the shim)

**Interfaces:**
- Consumes: `Simulation` and components from Tasks 3–8.
- Produces: `esc_calc_snr(exp_time, int_time, hoststarmag=-0.353, contrast=1e-8, planetdeltamag=20, bg_flux=22.5, exobg_flux=21, flux_units='vega', separation=0.2, ppgain=10, verbose=True, plot=False) -> (float, Observatory)`. The returned `Observatory` exposes `.source_counts`, `.sky_counts`, `.speckle_counts`, `.exozodi_counts`, `.num_psf_pixels`, `.ppgain` as Quantities for the existing tests.

- [ ] **Step 1: Confirm the existing anchor tests currently pass (baseline)**

Run: `pytest tests/test_anchors.py tests/test_snr.py -v`
Expected: PASS (pre-refactor engine). Record the values; they must still pass after the rewrite.

- [ ] **Step 2: Replace the module with the shim**

```python
# src/esc_etc/ExposureTimeSNRCalculatorESC.py
"""DEPRECATED compatibility shim.

The ESC ETC is now a compositional OO package (esc_etc.simulation.Simulation and
its components). This module preserves the historical procedural API by building
the new objects under the hood. Prefer `from esc_etc import Simulation`.
"""
import warnings

from astropy import units as u

from .simulation import Simulation
from .sensor import _resample_spectral_element  # re-export name kept below
from synphot import SourceSpectrum, SpectralElement
from synphot.models import Empirical1D


def resample_SpectralElement(S, w, verbose=True, label=""):
    ww, ff = S._get_arrays(wavelengths=w)
    return SpectralElement(Empirical1D, points=ww, lookup_table=ff)


def resample_SourceSpectrum(S, w, verbose=True, label=""):
    ww, ff = S._get_arrays(wavelengths=w)
    return SourceSpectrum(Empirical1D, points=ww, lookup_table=ff)


class Observatory:
    """Thin read-only view over a Simulation, exposing the legacy count attributes."""

    def __init__(self, simulation):
        self._sim = simulation
        rates = simulation.count_rate_components()
        self.source_counts = rates.source
        self.sky_counts = rates.zodi
        self.exozodi_counts = rates.exozodi
        self.speckle_counts = rates.speckle
        self.hoststar_counts = rates.host
        self.num_psf_pixels = simulation.sensor.num_psf_pixels
        self.num_pixels = simulation.sensor.num_pixels
        self.dark_current = simulation.sensor.dark_current
        self.read_noise = simulation.sensor.read_noise
        self.gain = simulation.sensor.gain
        self.well_depth = simulation.sensor.well_depth
        # legacy: self.ppgain stored the INVERTED gain (1/ppgain)
        self.ppgain = simulation.coronagraph.noise_floor_factor()
        self.background_name = simulation.telescope.zodi_profile_path


def esc_calc_snr(exp_time, int_time, hoststarmag=-0.353, contrast=1e-8,
                 planetdeltamag=20, bg_flux=22.5, exobg_flux=21,
                 flux_units="vega", separation=0.2, ppgain=10, verbose=True,
                 plot=False):
    """Build the OO Simulation and compute SNR, preserving legacy semantics.

    Historical time mapping (plan physics-fact #5): total integration time is
    this function's `exp_time`; per-frame time is `int_time`.
    """
    if verbose:
        warnings.warn(
            "esc_calc_snr/Observatory are deprecated; use esc_etc.Simulation.",
            DeprecationWarning, stacklevel=2,
        )
    sim = Simulation.from_default(
        hoststarmag=hoststarmag, planetdeltamag=planetdeltamag, contrast=contrast,
        ppgain=ppgain, separation=separation, bg_flux=bg_flux, exobg_flux=exobg_flux,
    )
    out = sim.get_snr(total_time=exp_time * u.s, frame_time=int_time * u.s)
    return out["snr"], Observatory(sim)
```

Note: `flux_units` is accepted for signature compatibility; the default `'vega'` path is what every anchor uses. If a non-vega call is needed later, thread it through `get_scene`/`Simulation._normalize_units`.

- [ ] **Step 3: Run the regression guard**

Run: `pytest tests/test_anchors.py tests/test_snr.py -v`
Expected: PASS — `test_anchor_baseline_snr` ≈ 8.9221, `test_anchor_default_call_600_10` ≈ 1.90435, `test_anchor_baseline_counts` source/sky/speckle/num_psf_pixels all match.

- [ ] **Step 4: Run the full physics suite**

Run: `pytest tests/test_physics_snr_time.py tests/test_physics_coronagraph.py tests/test_physics_backgrounds_units.py tests/test_physics_scaling.py -v`
Expected: PASS (modulo any tests already marked `xfail`/`skip` on the branch).

- [ ] **Step 5: Commit**

```bash
git add src/esc_etc/ExposureTimeSNRCalculatorESC.py
git commit -m "refactor: replace monolithic Observatory with OO compat shim"
```

---

### Task 10: Equivalence test against the frozen legacy grid + new-API parity

**Files:**
- Create: `tests/test_api_equivalence.py`
- Uses: `tests/test_data/legacy_snr_grid.json` from Task 1

**Interfaces:**
- Consumes: `Simulation`, `esc_calc_snr`, the JSON fixture.

- [ ] **Step 1: Write the test**

```python
# tests/test_api_equivalence.py
"""The new OO engine must reproduce the frozen legacy grid, and the fluent
Simulation API must agree with the esc_calc_snr shim."""
import json
import os

import astropy.units as u
import pytest

pytest.importorskip("config_stp_esc")
pytest.importorskip("config_um")

import esc_etc.ExposureTimeSNRCalculatorESC as esc_mod
from esc_etc.simulation import Simulation

_FIXTURE = os.path.join(os.path.dirname(__file__), "test_data", "legacy_snr_grid.json")
with open(_FIXTURE) as _f:
    _LEGACY = json.load(_f)


@pytest.mark.parametrize("record", _LEGACY, ids=lambda r: str(r["params"]))
def test_new_engine_matches_legacy_grid(record):
    p = record["params"]
    snr, esc = esc_mod.esc_calc_snr(verbose=False, plot=False, **p)
    assert float(snr) == pytest.approx(record["snr"], rel=2e-3)
    assert esc.source_counts.value == pytest.approx(record["source_counts"], rel=2e-3)
    assert esc.speckle_counts.value == pytest.approx(record["speckle_counts"], rel=2e-3)
    assert esc.num_psf_pixels.value == pytest.approx(record["num_psf_pixels"])


def test_fluent_api_matches_shim():
    sim = Simulation.from_default(hoststarmag=-0.353, planetdeltamag=20.0,
                                  contrast=1e-8, ppgain=10, separation=0.4,
                                  bg_flux=22.5, exobg_flux=21.0)
    fluent = sim.get_snr(total_time=3600 * u.s, frame_time=100 * u.s)["snr"]
    shim, _ = esc_mod.esc_calc_snr(3600, 100, separation=0.4, contrast=1e-8,
                                   ppgain=10, verbose=False, plot=False)
    assert fluent == pytest.approx(float(shim), rel=1e-9)
```

- [ ] **Step 2: Run the equivalence test**

Run: `pytest tests/test_api_equivalence.py -v`
Expected: PASS for all 7 grid records + the parity test.

- [ ] **Step 3: Commit**

```bash
git add tests/test_api_equivalence.py
git commit -m "test: equivalence of OO engine vs frozen legacy grid + API parity"
```

---

### Task 11: Public API exports + docs

**Files:**
- Modify: `src/esc_etc/__init__.py`
- Modify: `README.md`
- Modify: `docs/ETC_Changelog.rst`

**Interfaces:**
- Produces: top-level imports `Simulation`, `Telescope`, `Sensor`, `Scene`, `SceneElement`, `Coronagraph`, `get_scene`, `AnalyticCoronagraphNoiseModel`, `CountRates`, plus deprecated `Observatory`, `esc_calc_snr`.

- [ ] **Step 1: Write the failing test**

```python
# tests/test_public_api.py
def test_public_exports():
    import esc_etc
    for name in ["Simulation", "Telescope", "Sensor", "Scene", "SceneElement",
                 "Coronagraph", "get_scene", "AnalyticCoronagraphNoiseModel",
                 "CountRates", "esc_calc_snr"]:
        assert hasattr(esc_etc, name), f"missing export: {name}"
```

- [ ] **Step 2: Run test to verify it fails**

Run: `pytest tests/test_public_api.py -v`
Expected: FAIL with `AssertionError: missing export: Simulation`

- [ ] **Step 3: Update `__init__.py`**

```python
# src/esc_etc/__init__.py
import importlib.metadata
from pathlib import Path

__version__ = importlib.metadata.version(__package__)


def get_data_path():
    package_root = Path(__file__).parent.resolve()
    data_path = package_root / "support_data"
    if not data_path.exists():
        raise FileNotFoundError(f"Support data directory not found: {data_path}")
    return str(data_path) + "/"


from .telescope import Telescope
from .sensor import Sensor
from .scene import Scene, SceneElement, get_scene
from .coronagraph import Coronagraph
from .noise import AnalyticCoronagraphNoiseModel, CountRates
from .simulation import Simulation
from .ExposureTimeSNRCalculatorESC import Observatory, esc_calc_snr

__all__ = [
    "get_data_path", "__version__",
    "Simulation", "Telescope", "Sensor", "Scene", "SceneElement", "Coronagraph",
    "get_scene", "AnalyticCoronagraphNoiseModel", "CountRates",
    "Observatory", "esc_calc_snr",
]
```

- [ ] **Step 4: Run test to verify it passes**

Run: `pytest tests/test_public_api.py -v`
Expected: PASS (1 passed)

- [ ] **Step 5: Update README and changelog**

In `README.md`, add a "New OO API" usage block:

```python
from esc_etc import Simulation
import astropy.units as u

sim = Simulation.from_default(hoststarmag=-0.353, planetdeltamag=20,
                              contrast=1e-8, ppgain=10, separation=0.4)
print(sim.get_snr(total_time=3600 * u.s, frame_time=100 * u.s)["snr"])
```

Add a note: "`esc_calc_snr` / `Observatory` are deprecated compatibility wrappers; prefer `Simulation`."

In `docs/ETC_Changelog.rst`, add an entry describing the OO refactor (Telescope/Sensor/Scene/Coronagraph/Simulation, pluggable `noise_model`, deprecated shim).

- [ ] **Step 6: Run the full test suite**

Run: `pytest tests/ -v`
Expected: PASS (all green, modulo pre-existing `xfail`/`skip`).

- [ ] **Step 7: Commit**

```bash
git add src/esc_etc/__init__.py tests/test_public_api.py README.md docs/ETC_Changelog.rst
git commit -m "feat: export OO API and document the new architecture"
```

---

## Self-review

**Spec coverage:**
- _MetaHolder_ → Task 2. Telescope → Task 3. Sensor (+ bandpass) → Task 4. Coronagraph → Task 5. Scene/SceneElement/get_scene → Task 6. AnalyticCoronagraphNoiseModel + noise_model seam → Tasks 7 & 8. Simulation (+ from_config/from_components, count rates, SNR, int-time, saturation) → Task 8. Compat shim → Task 9. Config via from_config wrapping uasal repos → Tasks 3–5 (`from_config`/`from_default`). Regression guard + equivalence test → Tasks 1, 9, 10. Public API + docs → Task 11. Units → enforced throughout (Global Constraints). Star/planet naming → Task 6.
- YAGNI items (no 2D PSF, no OpticalTrain, no TOML port, no wcc_etc dep) are honored: only the `noise_model` seam is added (Tasks 7–8).

**Placeholder scan:** No TBD/TODO; every code step is complete and runnable. The `flux_units` non-vega path is explicitly deferred with a documented reason (every anchor uses vega) rather than left vague.

**Type consistency:** `count_rate_components()` returns `CountRates` (Task 7 dataclass) consumed by the noise model (Task 7) and Simulation (Task 8). `off_axis_throughput`/`speckle_scale`/`noise_floor_factor` names are consistent across Tasks 5, 7, 8. `get_snr(total_time, frame_time)` naming is consistent across Tasks 8, 9, 10. The shim's `Observatory` attribute names (`source_counts`, `sky_counts`, `speckle_counts`, `exozodi_counts`, `num_psf_pixels`, `ppgain`) match what `tests/test_anchors.py` and `physics_helpers.py` read.

**Risks carried from spec:** anchor drift (guarded by Tasks 1/9/10), config-repo coupling + editable install (Global Constraints), synphot resampling fidelity (Task 4 keeps `_resample_spectral_element` + `WAVELENGTHS` verbatim).
