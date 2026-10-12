API reference
=============

This reference is generated automatically from the docstrings in the source.
It is organized by module. The most commonly used objects are re-exported at
the top level of the ``esc_etc`` package, so e.g. ``esc_etc.Simulation`` and
``esc_etc.simulation.Simulation`` are the same class.

Top-level public API
--------------------

``esc_etc.FILTERS`` is the dictionary of ESC filter names (wheel slot and
designation) accepted by ``filter=``.

.. currentmodule:: esc_etc

.. autosummary::
   :nosignatures:

   Simulation
   Telescope
   Sensor
   Scene
   SceneElement
   get_scene
   Coronagraph
   AnalyticCoronagraphNoiseModel
   CountRates
   plot_count_rates
   plot_snr_vs_time
   plot_offaxis_throughput
   plot_bandpass
   plot_spectra
   plot_aperture
   plot_overview
   lazuli_style
   use_lazuli_style
   get_data_path

Modules
-------

.. toctree::
   :maxdepth: 2

   simulation
   telescope
   sensor
   scene
   coronagraph
   noise
   plotting
   uasal_config
   legacy
