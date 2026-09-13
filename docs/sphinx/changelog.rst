Changelog
=========

This page summarizes notable changes. The authoritative history is the git log
and the design specs under ``docs/superpowers/``. A detailed list of the changes
made since the original fork is kept in ``docs/ETC_Changelog.rst``.

Physics
-------

- **One photometric aperture** (issue #10). ``Sensor.num_psf_pixels`` is now
  :attr:`Telescope.resel <esc_etc.Telescope.resel>` :math:`= \pi(\lambda/2D)^2`
  in detector pixels (about 30 at the default configuration) instead of a
  separate :math:`15 \times 15` PSF box, so dark current, read noise, zodi and
  exozodi all use the same extraction aperture. ``Sensor.calc_psf`` is removed.
  The FPM off-axis throughput is documented as the planet's throughput into that
  aperture and raw contrast as leakage relative to the off-axis PSF in it.
  Default-configuration SNR anchors moved accordingly.
- **Peak-pixel saturation model** (issue #11).
  :meth:`~esc_etc.Simulation.saturation_time` now fills the brightest dark-hole
  pixel: point sources contribute ``Sensor.peak_pixel_fraction`` of their
  in-aperture rate (default from the Airy pattern at the plate scale), diffuse
  backgrounds spread over the aperture, dark current is included, and the limit
  is ``Sensor.headroom`` (default 0.8) times the well depth. Both new sensor
  parameters are mutable. The occulted host remains out of scope.
- **Integer frame accounting and input validation** (issue #15). Read noise
  scales with ``ceil(total_time / frame_time)`` reads (whole frames plus a
  shorter final one, at least one).
  :meth:`~esc_etc.Simulation.get_int_time_for_snr` returns ``int_time`` rounded
  up to whole frames plus ``int_time_continuous``, both in seconds. Non-positive
  times, target SNR, ``ppgain`` or separation and negative contrast raise
  ``ValueError``; separations outside the FPM table raise instead of clamping; a
  saturating ``frame_time`` warns. A rejected ``update`` leaves no trace. The
  default :func:`~esc_etc.plot_snr_vs_time` grid starts at one frame.
- **Planet spectrum is used** (issue #13). The planet's ``spectrum`` is
  normalized ``deltamag`` fainter than the host in ``deltamag_band`` (default:
  the ESC band, which reproduces the old :math:`10^{-0.4\,\Delta m}` scaling;
  or a filter name such as ``"johnson_v"``) and observed through the ESC
  bandpass, so planet colour matters when the contrast is quoted elsewhere.
  ``spectrum`` and ``deltamag_band`` are mutable; ``planet.mag`` is unused.
- **Explicit reference bands** (issue #14). Every :class:`~esc_etc.SceneElement`
  carries a mutable ``band`` (``None`` = ESC bandpass, a synphot filter name, or
  a ``SpectralElement``); spectra are normalized there, then integrated through
  the ESC bandpass. :func:`~esc_etc.get_scene` and
  :meth:`Simulation.from_default <esc_etc.Simulation.from_default>` take
  ``hoststar_band`` (``"johnson_v"`` for catalog photometry) and ``mag_system``.
  Zodi is explicitly Johnson *V*; ``exobg_flux`` is documented as a delta
  magnitude. Invalid magnitude systems raise ``ValueError`` immediately, and the
  deprecated ``flux_units`` argument is now honored instead of ignored.
- **End-of-life ESC filter curves**. Twelve telescope + ESC throughput curves
  (EOL, 5% telescope and 10% ESC reserve, detector QE included, FPM excluded)
  ship in ``esc_etc/data/esc_filters_eol`` and are listed in
  :data:`esc_etc.FILTERS` by wheel slot (``"R1"``) and designation
  (``"F620N"``). ``filter=`` on :meth:`Simulation.from_default
  <esc_etc.Simulation.from_default>`, ``Telescope.from_default`` and
  ``Sensor.from_default`` uses the curve as the whole sensor bandpass and the
  design wavelength as the telescope's central wavelength (resel, lambda/D).
  Default (``None``) keeps the generic config box filter. The curves were
  generated from the ``config_stp_esc`` chain (Al+MgF2 optics, ASI6200MM QE)
  and peak about 3.5x below the ``config_um_esc`` default chain; see
  ``report/`` for the audit.
- **3 m Ultramarine default** (``config_um_esc``). ``from_default`` on every
  component now reads the ESC instrument from ``config_um_esc`` (3.0 m clear
  aperture, ASI294MM, silver ESC optics, 0.9 dichroic) instead of
  ``config_stp_esc`` (2.43 m, ASI6200MM, Al+MgF2), matching the telescope in
  ``config_um``. ``config_um_esc`` is a required dependency; ``config_stp_esc``
  moves to the ``dev`` extra. The bandpass chain applies
  ``dichroic_throughput`` when the config has one, and the detector tables are
  clamped at their ends so the -20 C nominal temperature no longer raises.
  Default source rates rise 5.9x (area 1.56 x throughput 3.52 x FPM 1.07) and
  every golden anchor was re-pinned accordingly.
- **Reference-subtraction noise and time** (issue #12).
  :class:`~esc_etc.Coronagraph` gains ``subtraction`` (``"none"`` default, or
  ``"rdi"``), ``ref_brightness_ratio`` and ``ref_time_ratio``. Under RDI the
  scaled random variance of the reference image is added to the science
  variance (Nemati et al. 2023) and the inversion accounts for it.
  ``total_time`` is on-target science time; results carry ``science_time``,
  ``charged_time`` and ``reference_noise_e``, and ``noise_terms`` gains a
  sixth, reference entry. ``ppgain`` is documented as an assumed residual-
  speckle factor.

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
  (:attr:`~esc_etc.Sensor.well_depth`, ``num_psf_pixels``), and the frame-time
  trade-off against read noise.
- A ``docs`` extra in ``pyproject.toml`` for a one-line local docs build
  (``pip install -e ".[docs]"``).

Earlier history
---------------

The package was forked from the UASAL Exposure Time Calculator (originally by
Aaron Goldtooth) in July 2024. The intervening refactors — config-driven
structure, an installable package with setuptools_scm versioning, corrected unit
handling and read-noise treatment, and Johnson-V sky-background normalization —
are documented in ``docs/ETC_Changelog.rst``.
