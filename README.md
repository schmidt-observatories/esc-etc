# STP ETC ESC

This is intended to be the active directory for the public release of the exposure time calculator for the ExtraSolar Camera.

Derived from the exposure time calculator developed by Aaron Goldtooth, with updates from Justin Hom.

Additional Contributions from Sanchit Sabhlok and Jess Johnson.

## Requirements
All important properties related to the instrument including mirrors, optics, coating throughput, filters, and detectors, are stored in the repositories outlined below. 

> [!Note] 
> The exposure time calculator also allows for users to input their own configurations, **but** this feature can only be used if the configuration(s) follow the same organizational structure as defined in these configuration repositories listed. 
> 
> Users can also use the class functions built into the backend to create their own instruments for calculating exposure times.

The installation instructions for these packages can be found on their corresponding GitHub repos. 

### Telescope

1. [config_um](https://github.com/uasal/config_um) - The configuration repo for UA Ultramarine 3m telescope concept.
2. [config_stp](https://github.com/uasal/config_stp) - The configuration repo for the Space Telescope Project 6.5m (https://arxiv.org/abs/2309.04934).

### Instrument
1. [config_stp_esc](https://github.com/uasal/config_stp_esc) - Configuration repo for the ESC instrument.

### UASAL Archive

For full functionality including stellar and galactic spectra, you will need to set up access to the [UASAL archive](https://github.com/uasal/uasal_archive) and add a path variable `$UASAL_ARCHIVE` to your environment, pointing to the location of the cloned UASAL Archive directory. 

The installation instructions for these packages can be found on their corresponding GitHub repos. 

## Dependencies

All UASAL config packages are dependent on [utils_config](https://github.com/uasal/utils_config) but will be automatically installed when installing the configuration repositories.

Additional package dependencies required for the ETC - astropy, numpy, matplotlib, scipy and synphot.

## Installation

The Exposure Time Calculator is a python package that can be installed via a download from GitHub and then installing on your system locally. You can directly clone the [STP ETC ESC GitHub Repo](https://github.com/uasal/stp_etc_esc) or fork the repo and clone the fork. 

```
$ git clone https://github.com/uasal/stp_etc_esc.git
$ cd stp_etc_esc
$ pip install .
```
> [!Note]
> To install package with optional dependencies *(ex. config_stp, config_um, pytest, etc...)*, run the following pip command instead:<br>
> 
> `pip install '.[dev]'`<br>
> **OR**<br>
> `pip install ".[dev]"`
>
> Pytests will be able to be used when installing `stp_etc_esc` with the `.[dev]` command.

The ETC should now be installed on your local machine. To confirm installation, the following import on python should work - 
```
import esc_etc
esc_etc.__version__
```

## Usage

Included in this repository is an [example notebook](https://github.com/uasal/stp_etc_esc/blob/develop/notebooks/ESC_ExposureTimeSNRCalculator_Demo.ipynb) of how to use the exposure time calculator assuming the default configurations. There is also an [executable python script](https://github.com/uasal/stp_etc_esc/blob/develop/notebooks/etc_esc_requirements.py) that will run the exposure time calculator assuming the default configurations and generate figures calculating SNR and noise sources for various individual frame exposure times.

### New OO API

The package now exposes a clean object-oriented API. The recommended entry point is `Simulation`:

```python
from esc_etc import Simulation
import astropy.units as u

sim = Simulation.from_default(hoststarmag=-0.353, planetdeltamag=20,
                              contrast=1e-8, ppgain=10, separation=0.4)
print(sim.get_snr(total_time=3600 * u.s, frame_time=100 * u.s)["snr"])
```

The full set of top-level exports includes: `Telescope`, `Sensor`, `Scene`, `SceneElement`, `get_scene`, `Coronagraph`, `AnalyticCoronagraphNoiseModel`, `CountRates`, and `Simulation`.

> [!Note]
> `esc_calc_snr` / `Observatory` are deprecated compatibility wrappers; prefer `Simulation`.

### Plotting

The package ships a suite of lazuli-styled matplotlib helpers:

```python
from esc_etc import Simulation, plot_count_rates, plot_snr_vs_time

sim = Simulation.from_default(separation=0.4, contrast=1e-8, ppgain=10)
fig, ax = plot_count_rates(sim)          # noise-contributor breakdown
fig, ax = plot_snr_vs_time(sim)          # SNR vs integration time (lazuli style)
```

All helpers use the packaged `lazuli.mplstyle` automatically (no global state mutation).
Call `use_lazuli_style()` to apply the style globally to your own plots.
Each helper returns `(fig, ax)` and opens a matplotlib figure; close figures you don't keep (`plt.close(fig)`) when generating many in a loop.

### Tutorials

A numbered suite of runnable Jupyter tutorials in [`notebooks/`](notebooks/) walks through the new OO API and the plotting helpers (they require the `config_um` / `config_stp_esc` configs and an editable install):

- [`01_getting_started.ipynb`](notebooks/01_getting_started.ipynb) — build a `Simulation`, compute SNR, and plot the noise breakdown.
- [`02_components_and_parameters.ipynb`](notebooks/02_components_and_parameters.ipynb) — build `Telescope`/`Sensor`/`Scene`/`Coronagraph` individually, assemble with `from_components`, and vary parameters via `update()`/`reset()`.
- [`03_coronagraph_and_contrast.ipynb`](notebooks/03_coronagraph_and_contrast.ipynb) — the coronagraph knobs (`raw_dh_contrast`, `ppgain`, `separation`) and the off-axis throughput curve.
- [`04_integration_time_snr_saturation.ipynb`](notebooks/04_integration_time_snr_saturation.ipynb) — invert SNR for an integration time, the SNR-vs-time curve, and saturation.

> [!Note]
> The older `ESC_ExposureTimeSNRCalculator_Demo.ipynb` is legacy (deprecated API); prefer the numbered suite above.




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

> [!Note]
> `pip install -e ".[docs]"` also installs the UASAL config git dependencies. If
> you only want to build the docs and don't have access to those repos, use the
> dependency-free path that CI and Read the Docs use instead:
> ```bash
> pip install -r docs/sphinx/requirements.txt
> pip install -e . --no-deps
> ```
> The config packages are imported lazily inside `from_default` / `from_config`
> and are mocked for the docs build, and the tutorial notebooks render from their
> saved outputs, so nothing is executed at build time.

The site is built and published by the
[`Docs` workflow](.github/workflows/deploy-docs.yml) on every push to `main`
(GitHub Pages), and a [`.readthedocs.yaml`](.readthedocs.yaml) is included so it
also builds on Read the Docs once the repository is connected there.
