Changelog
=========

This page summarizes notable changes. The authoritative history is the git log
and the design specs under ``docs/superpowers/``. A detailed list of the changes
made since the original fork is kept in ``docs/ETC_Changelog.rst``.

Object-oriented API
-------------------

- **Composable class API.** The ETC exposes a suite of composable classes at the
  top level: :class:`~esc_etc.Telescope`, :class:`~esc_etc.Sensor`,
  :class:`~esc_etc.Scene` / :class:`~esc_etc.SceneElement` /
  :func:`~esc_etc.get_scene`, :class:`~esc_etc.Coronagraph`,
  :class:`~esc_etc.AnalyticCoronagraphNoiseModel`, :class:`~esc_etc.CountRates`,
  and :class:`~esc_etc.Simulation`.
- **Pluggable noise model.** The noise model is swappable via the
  ``noise_model`` seam on :class:`~esc_etc.Simulation`, enabling custom noise
  implementations (e.g. a future 2-D PSF image model) without subclassing the
  simulation engine.
- :meth:`Simulation.from_default <esc_etc.Simulation.from_default>` and the
  per-component ``from_config`` / ``from_default`` constructors replace direct
  use of ``Observatory``. The legacy :class:`~esc_etc.Observatory` class and
  :func:`~esc_etc.esc_calc_snr` function are retained as **deprecated**
  compatibility wrappers and will be removed in a future release.

Plotting
--------

- **New** :mod:`esc_etc.plotting` **module** with five lazuli-styled matplotlib
  helpers: :func:`~esc_etc.plot_count_rates` (noise-contributor bar breakdown),
  :func:`~esc_etc.plot_snr_vs_time` (SNR vs integration time),
  :func:`~esc_etc.plot_offaxis_throughput` (coronagraph off-axis throughput vs
  separation), :func:`~esc_etc.plot_bandpass` (sensor bandpass curve), and
  :func:`~esc_etc.plot_spectra` (scene-element spectra overlay).
- A packaged ``lazuli.mplstyle`` ships as package data and is applied inside each
  helper via a context manager (no global state mutation). Style utilities
  :func:`~esc_etc.lazuli_style` / :func:`~esc_etc.use_lazuli_style` and the color
  tokens ``TEAL`` / ``RED`` / ``AMBER`` / ``BLUE`` / ``GREEN`` / ``DARKBLUE`` /
  ``LAZULI_COLORS`` are exported from the top-level namespace.

Tutorials
---------

- **New numbered tutorial-notebook suite** in ``notebooks/`` teaching the
  object-oriented API and the plotting helpers: ``01_getting_started``,
  ``02_components_and_parameters``, ``03_coronagraph_and_contrast``, and
  ``04_integration_time_snr_saturation``. Each notebook executes end to end and
  prints reference sanity values.

Documentation site
------------------

- **Sphinx documentation site** under ``docs/sphinx/`` (Read the Docs theme):
  installation, quickstart, configuration, a user guide, the tutorial notebooks
  rendered via ``nbsphinx``, and an autodoc API reference. Built and published
  to GitHub Pages by ``.github/workflows/deploy-docs.yml``; a
  ``.readthedocs.yaml`` is included for Read the Docs.
- **New** :doc:`user_guide/saturation` **page** covering
  :meth:`~esc_etc.Simulation.saturation_time` and
  :meth:`~esc_etc.Simulation.is_saturated`, what sets the per-pixel rate
  (:attr:`~esc_etc.Sensor.well_depth`, :meth:`Sensor.calc_psf
  <esc_etc.Sensor.calc_psf>`), and the frame-time trade-off against read noise.
- A ``docs`` extra in ``pyproject.toml`` for a one-line local docs build
  (``pip install -e ".[docs]"``).

Earlier history
---------------

The package was forked from the UASAL Exposure Time Calculator (originally by
Aaron Goldtooth) in July 2024. The intervening refactors — config-driven
structure, an installable package with setuptools_scm versioning, corrected unit
handling and read-noise treatment, and Johnson-V sky-background normalization —
are documented in ``docs/ETC_Changelog.rst``.
