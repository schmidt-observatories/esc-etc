esc-etc: Exposure Time Calculator for the Lazuli ESC
====================================================

.. image:: _static/logo_schmidt_observatory_system.png
   :alt: Schmidt Observatory System
   :width: 320px

**esc-etc** is the exposure time calculator (ETC) for the **ExtraSolar Camera
(ESC)**, the coronagraphic instrument on *Lazuli* — the flagship instrument of
the Schmidt Observatory System. It composes a *telescope*, a *sensor*, an
observable *scene* (host star, planet, zodiacal and exozodiacal backgrounds),
and a *coronagraph*, then returns coronagraphic signal-to-noise ratios,
required integration times, and saturation estimates, along with ready-made
diagnostic plots.

.. note::

   New here? Read :doc:`installation` and then work through
   :doc:`quickstart`. The :doc:`tutorials` are runnable Jupyter notebooks that
   cover the object-oriented API end to end.

Highlights
----------

- **Composable object model** — :class:`~esc_etc.Telescope`,
  :class:`~esc_etc.Sensor`, :class:`~esc_etc.Scene`, and
  :class:`~esc_etc.Coronagraph` assembled into a single
  :class:`~esc_etc.Simulation`, the recommended entry point.
- **Coronagraphic noise model** — an analytic SNR engine
  (:class:`~esc_etc.AnalyticCoronagraphNoiseModel`) accounting for the planet
  source, zodiacal and exozodiacal light, residual speckle with a
  post-processing noise floor, dark current, and read noise.
- **Coronagraph physics** — raw dark-hole contrast, post-processing gain, planet
  separation, and the off-axis (focal-plane mask) :math:`\lambda/D` throughput
  curve applied as a flat scalar to every count rate.
- **Integration-time inversion** — solve for the integration time that reaches a
  target SNR, with per-frame saturation checks.
- **Plotting** — lazuli-styled matplotlib helpers for the count-rate / noise
  breakdown, SNR vs. integration time, off-axis throughput, sensor bandpass, and
  scene spectra.

A configurable instrument
--------------------------

Instrument and telescope properties (mirrors, optics, coatings, filters,
detectors) live in the UASAL configuration repositories — ``config_um`` (the UA
Ultramarine 3 m telescope concept) and ``config_stp_esc`` (the ESC instrument).
:meth:`Simulation.from_default <esc_etc.Simulation.from_default>` pulls these in
for you; see :doc:`configuration` for the details and for how to supply your
own.

Contents
--------

.. toctree::
   :maxdepth: 2
   :caption: Getting started

   installation
   quickstart

.. toctree::
   :maxdepth: 2
   :caption: User guide

   user_guide/index

.. toctree::
   :maxdepth: 2
   :caption: Tutorials

   tutorials

.. toctree::
   :maxdepth: 2
   :caption: Reference

   api/index
   configuration
   changelog

Indices and tables
-------------------

* :ref:`genindex`
* :ref:`modindex`
* :ref:`search`
