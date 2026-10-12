# ESC ETC

This is intended to be the active directory for the public release of the exposure time calculator for the ExtraSolar Camera.

Derived from the exposure time calculator developed by Aaron Goldtooth, with updates from Justin Hom.

Additional Contributions from Sanchit Sabhlok and Jess Johnson.

## Requirements

Python 3.11 or newer, plus astropy, numpy, scipy, matplotlib, pandas and synphot (installed automatically).

All instrument and telescope properties (mirrors, coatings, filters, detector tables) come from the UASAL configuration repositories [config_um](https://github.com/uasal/config_um) (UA Ultramarine 3 m telescope) and [config_um_esc](https://github.com/uasal/config_um_esc) (ESC instrument). A snapshot of those files is **vendored inside the package** under `src/esc_etc/data/uasal/` (provenance in `SNAPSHOT.txt`), so a plain `pip install` needs no git access. Maintainers refresh the snapshot with:

```
$ pip install -r scripts/requirements-uasal.txt
$ python scripts/sync_uasal_configs.py
```

> [!Note]
> The exposure time calculator also allows for users to input their own configurations via the `from_config` class methods, **but** the configuration(s) must follow the same organizational structure as the UASAL configuration repositories.

## Installation

The Exposure Time Calculator is a python package. Once released it installs from PyPI with `pip install esc_etc`. For development, clone the [ESC ETC GitHub Repo](https://github.com/schmidt-observatories/esc-etc) or fork the repo and clone the fork. 

```
$ git clone https://github.com/schmidt-observatories/esc-etc.git
$ cd esc-etc
$ pip install -e .
```
> [!Important]
> Use an **editable** install (`pip install -e .`). A plain `pip install .` copies the package into `site-packages` and can shadow the repository's `src/` tree, reintroducing import/version surprises. For development always prefer `-e`.

> [!Note]
> To install the package with the development dependencies *(pytest, build, twine)*, run the following pip command instead:<br>
> 
> `pip install -e '.[dev]'`<br>
> **OR**<br>
> `pip install -e ".[dev]"`
>
> Pytests will be able to be used when installing `esc_etc` with the `.[dev]` command.

The ETC should now be installed on your local machine. To confirm installation, the following import on python should work - 
```
import esc_etc
esc_etc.__version__
```

## Usage

The entry point is `Simulation`. Times may be astropy quantities or plain numbers in seconds.

```python
from esc_etc import Simulation

sim = Simulation.from_default(hoststarmag=-0.353, planetdeltamag=20,
                              contrast=1e-8, ppgain=10, separation=0.4)
sim.get_snr(total_time=3600, frame_time=100)["snr"]     # ~9.87
sim.get_int_time_for_snr(5, frame_time=100)["int_time"]  # whole frames to reach SNR 5
sim.saturation_time()                                     # frame time that fills the well
```

Useful options on `from_default`:

- `filter="F630N"` (any key of `esc_etc.FILTERS`) uses that ESC filter's measured curve as the bandpass; `lifetime="eol"` (default) or `"bol"` picks the end- or beginning-of-life curve set.
- Any parameter can be changed afterwards with `sim.update(coronagraph__ppgain=20)` and put back with `sim.reset()`. The sensor's `aperture` (`"resel"`, `"optimal"`, `"box"`, `"matched"`) and `encircled_energy` override are set the same way.

Top-level exports: `Simulation`, `Telescope`, `Sensor`, `Scene`, `SceneElement`, `get_scene`, `Coronagraph`, `AnalyticCoronagraphNoiseModel`, `CountRates`, `FILTERS`, plus the plotting helpers below. `esc_calc_snr` and `Observatory` are deprecated compatibility wrappers.

### Plotting

Every standard plot is a method on the object that owns the data, accepts `ax=` and returns `(fig, ax)`:

```python
fig, axes = sim.plot()                                  # 2 x 3 overview
fig, ax = sim.plot_snr_vs_time()
fig, ax = sim.plot_snr_vs_time(sweep={"coronagraph__raw_dh_contrast": [1e-7, 1e-8, 1e-9]})
fig, ax = sim.plot_count_rates()
fig, ax = sim.sensor.plot_bandpass(ax=my_ax)            # draw onto your own axis
fig, ax = sim.sensor.plot_aperture()
fig, ax = sim.coronagraph.plot_offaxis_throughput()
fig, ax = sim.scene.plot_spectra()
```

The same plots exist as functions in `esc_etc.plotting` (`plot_count_rates(sim)`, `plot_snr_vs_time(total_times=..., snrs=...)`, and so on) for raw arrays. All of them use the packaged `lazuli.mplstyle` through a context manager; `use_lazuli_style()` applies it to your own plots.

### Tutorials

Four runnable Jupyter notebooks in [`notebooks/`](notebooks/), rendered in the documentation site. Only an editable install is needed.

- [`01_getting_started.ipynb`](notebooks/01_getting_started.ipynb): SNR, integration time, count rates, the overview plot.
- [`02_components_and_parameters.ipynb`](notebooks/02_components_and_parameters.ipynb): the four components, apertures, filters, `update()` and `reset()`.
- [`03_coronagraph_and_contrast.ipynb`](notebooks/03_coronagraph_and_contrast.ipynb): contrast, post-processing gain, separation and reference subtraction, with parameter sweeps.
- [`04_integration_time_snr_saturation.ipynb`](notebooks/04_integration_time_snr_saturation.ipynb): frame time and read noise, inverting for time, saturation.

The notebooks are generated by `scripts/build_tutorials.py` and executed with `jupyter nbconvert --execute`; edit the script, not the JSON. `ESC_ExposureTimeSNRCalculator_Demo.ipynb` and `etc_esc_requirements.py` use the pre-refactor API and do not run.

## Tests

`pip install -e ".[dev]"` then `pytest`. The same suite runs on every pull request through `.github/workflows/tests.yml`.

## Documentation

The full documentation site — installation, a user guide, the rendered tutorial
notebooks, and an auto-generated API reference — is built with **Sphinx** and the
*Read the Docs* theme. It lives under [`docs/sphinx/`](docs/sphinx/).

To build it locally:

```bash
pip install -e ".[docs]"   # Sphinx + theme + nbsphinx (+ the package itself)
brew install pandoc        # or: conda install pandoc / apt-get install pandoc
cd docs/sphinx
make html                  # output in _build/html/index.html
```

The tutorial notebooks render from their saved outputs, so nothing is executed at build time. CI and Read the Docs use `pip install -r docs/sphinx/requirements.txt && pip install -e .`.

The site is built and published by the
[`Docs` workflow](.github/workflows/deploy-docs.yml) on every push to `main`
(GitHub Pages), and a [`.readthedocs.yaml`](.readthedocs.yaml) is included so it
also builds on Read the Docs once the repository is connected there.
