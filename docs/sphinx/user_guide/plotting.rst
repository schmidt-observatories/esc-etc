Plotting
========

The :mod:`esc_etc.plotting` module ships five lazuli-styled matplotlib helpers.
Each one applies the packaged ``lazuli.mplstyle`` internally via a context
manager (so it does not mutate global matplotlib state) and returns
``(fig, ax)``.

The helpers
-----------

.. list-table::
   :header-rows: 1
   :widths: 32 68

   * - Helper
     - What it plots
   * - :func:`~esc_etc.plot_count_rates`
     - Bar chart of the count-rate / noise contributors (source, zodi, exozodi,
       speckle, dark current) for a simulation.
   * - :func:`~esc_etc.plot_snr_vs_time`
     - SNR as a function of integration time.
   * - :func:`~esc_etc.plot_offaxis_throughput`
     - Coronagraph off-axis (FPM) throughput vs. separation.
   * - :func:`~esc_etc.plot_bandpass`
     - The sensor's optical bandpass (throughput vs. wavelength).
   * - :func:`~esc_etc.plot_spectra`
     - Overlay of the scene-element spectra (star / planet / zodi, by default).

Typical usage
-------------

Pass a :class:`~esc_etc.Simulation` (or the relevant component) and the helper
figures out the rest:

.. code-block:: python

   from esc_etc import (
       Simulation, plot_count_rates, plot_snr_vs_time,
       plot_offaxis_throughput, plot_bandpass, plot_spectra,
   )

   sim = Simulation.from_default(separation=0.4, contrast=1e-8, ppgain=10)

   fig, ax = plot_count_rates(sim)                  # noise breakdown
   fig, ax = plot_snr_vs_time(sim)                  # SNR vs integration time
   fig, ax = plot_offaxis_throughput(sim.coronagraph)
   fig, ax = plot_bandpass(sim.sensor)
   fig, ax = plot_spectra(sim.scene)

Most helpers also accept explicit arrays (e.g. ``rates`` + ``sensor``, or
``total_times`` + ``frame_time``) instead of a simulation, and an ``ax=`` to draw
onto an existing axis. See the :doc:`../api/plotting` reference for the full
signatures.

.. tip::

   When generating many figures in a loop, close the ones you do not keep with
   ``plt.close(fig)`` to avoid accumulating open figures.

The house style
---------------

The same style is available for your own plots without touching the ETC:

.. code-block:: python

   from esc_etc import lazuli_style, use_lazuli_style

   use_lazuli_style()             # apply globally to the current session

   with lazuli_style():           # or scope it to a block
       ...                        # your plotting code

The exported color tokens — ``TEAL``, ``RED``, ``AMBER``, ``BLUE``, ``GREEN``,
``DARKBLUE``, and the ``LAZULI_COLORS`` sequence — match the palette the helpers
use.
