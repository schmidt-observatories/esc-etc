Plotting
========

Every standard plot is a method on the object that owns the data. Each one
accepts ``ax=`` to draw onto an existing axis, applies the packaged
``lazuli.mplstyle`` through a context manager (no global matplotlib state is
changed), and returns ``(fig, ax)``.

The methods
-----------

.. list-table::
   :header-rows: 1
   :widths: 40 60

   * - Method
     - What it plots
   * - ``sim.plot()``
     - A 2 x 3 overview: the six panels below. Returns ``(fig, axes)``.
   * - ``sim.plot_count_rates()``
     - Bar chart of the count-rate contributors (source, zodi, exozodi,
       speckle, dark current).
   * - ``sim.plot_snr_vs_time()``
     - SNR as a function of integration time; see the sweeps below.
   * - ``sim.plot_bandpass()`` / ``sim.sensor.plot_bandpass()``
     - The sensor's optical bandpass (throughput vs. wavelength).
   * - ``sim.plot_aperture()`` / ``sim.sensor.plot_aperture()``
     - The photometric aperture drawn over a pixel-integrated Airy PSF.
   * - ``sim.plot_offaxis_throughput()`` / ``sim.coronagraph.plot_offaxis_throughput()``
     - Coronagraph off-axis (FPM) throughput vs. separation, with the current
       separation marked.
   * - ``sim.plot_spectra()`` / ``sim.scene.plot_spectra()``
     - The scene-element spectra (star, planet and zodi by default).

Parameter sweeps
----------------

``plot_snr_vs_time`` takes ``sweep=``, a one-entry dictionary naming any
parameter you could pass to :meth:`~esc_etc.Simulation.update` and the values
to try. One curve is drawn per value and the original value is put back:

.. code-block:: python

   sim.plot_snr_vs_time(sweep={"coronagraph__raw_dh_contrast": [1e-7, 1e-8, 1e-9]})
   sim.plot_snr_vs_time(sweep={"coronagraph__ppgain": [1, 10, 100]})
   sim.plot_snr_vs_time(sweep={"scene__zodi__mag": [22.5, 20, 17.5]})

Several curves on one axis
--------------------------

``plot_snr_vs_time``, ``plot_bandpass`` and ``plot_offaxis_throughput`` take
``label=``; with ``ax=`` that gives a legend without touching the lines:

.. code-block:: python

   import matplotlib.pyplot as plt
   fig, ax = plt.subplots()
   for ft in [10, 100, 1000]:
       sim.plot_snr_vs_time(frame_time=ft, ax=ax, label=f"frame time {ft} s")

   fig, ax = plt.subplots()
   Simulation.from_default(filter="F630N", lifetime="eol").plot_bandpass(ax=ax, label="EOL")
   Simulation.from_default(filter="F630N", lifetime="bol").plot_bandpass(ax=ax, label="BOL")

The functions behind the methods
--------------------------------

The methods are one-line delegates to :mod:`esc_etc.plotting`, whose functions
also accept raw arrays instead of a simulation (``rates`` + ``sensor``,
``total_times`` + ``snrs``, ``wavelength`` + ``throughput``, and so on). See
the :doc:`../api/plotting` reference for the signatures.

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

The exported color tokens ``TEAL``, ``RED``, ``AMBER``, ``BLUE``, ``GREEN``,
``DARKBLUE``, and the ``LAZULI_COLORS`` sequence match the palette the helpers
use.
