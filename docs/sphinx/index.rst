esc-etc: Exposure Time Calculator for the Lazuli ESC
====================================================

.. image:: _static/logo_schmidt_observatory_system.png
   :alt: Schmidt Observatory System
   :width: 320px

**esc-etc** is the exposure time calculator (ETC) for the ExtraSolar Camera
(ESC), the coronagraphic instrument on *Lazuli*, the Schmidt Observatory
System's space telescope. You describe a host star, a planet and the sky
background, pick a filter and a coronagraph setting, and it returns the
signal-to-noise ratio for a given integration time, the integration time that
reaches a target signal-to-noise, and the longest frame the detector can take
before the brightest pixel saturates. Each result can also be drawn with one
method call.

A hosted web version of the ETC is available at
`simulators.schmidtobservatorysystem.org/esc <https://simulators.schmidtobservatorysystem.org/esc/>`_.

.. note::

   New here? Read :doc:`installation`, then :doc:`quickstart`. If coronagraph
   vocabulary (dark hole, raw contrast, post-processing gain) is new to you,
   the primer at the top of :doc:`user_guide/coronagraph` defines the terms
   the rest of this site uses.

What it models
--------------

- A calculation is built from four objects, a :class:`~esc_etc.Telescope`, a
  :class:`~esc_etc.Sensor`, a :class:`~esc_etc.Scene` (host star, planet,
  zodiacal and exozodiacal light) and a :class:`~esc_etc.Coronagraph`,
  combined into one :class:`~esc_etc.Simulation`.
- The noise budget counts photon noise from the planet, the sky backgrounds and
  the residual starlight (speckles), dark current, read noise per frame, and a
  systematic floor from the speckles that post-processing does not remove.
  That floor gives every configuration a maximum reachable signal-to-noise.
- The coronagraph is described by its raw dark-hole contrast, an assumed
  post-processing gain, the planet separation and a throughput curve for the
  focal-plane mask. Reference-star subtraction can be switched on.
- ``filter="F630N"``, or any of the twelve ESC filters, uses that filter's
  measured end-to-end throughput, at end of life or at beginning of life.
- Photometry is done in a chosen aperture: the resolution element by default,
  or an optimal, box or matched aperture, each with its own encircled energy.
- Integration time can be solved for a target signal-to-noise, and every frame
  time is checked against saturation.
- ``sim.plot()`` draws a six-panel overview. The simulation, sensor, scene and
  coronagraph have ``plot_*(ax=None)`` methods for the count-rate budget, SNR
  against time (with parameter sweeps), the mask throughput, the bandpass, the
  aperture footprint and the scene spectra.

Where the instrument comes from
-------------------------------

The telescope and instrument properties (mirrors, coatings, filters, detector
tables) come from configuration files for the Lazuli 3 m telescope and the
ESC, maintained by the University of Arizona Space Astrophysics Laboratory
(UASAL). A snapshot of those files ships inside ``esc_etc``, so nothing else
is installed. :doc:`configuration` lists
what is in the snapshot and how to point the ETC at your own instrument.

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
   limitations
   changelog

Indices and tables
-------------------

* :ref:`genindex`
* :ref:`modindex`
* :ref:`search`
