Plotting
========

Every standard plot is a method on the object that owns the data. Each one
accepts ``ax=`` to draw onto an existing axis, applies the packaged
``lazuli.mplstyle`` through a context manager so that your own matplotlib
settings are left alone, and returns ``(fig, ax)``. The figures on this page
are produced at build time from the code shown above them, for the default
simulation:

.. plot::
   :context: reset
   :nofigs:

   from esc_etc import Simulation

   sim = Simulation.from_default(hoststarmag=-0.353, planetdeltamag=20,
                                 contrast=1e-8, ppgain=10, separation=0.4)

The methods
-----------

.. list-table::
   :header-rows: 1
   :widths: 40 60

   * - Method
     - What it plots
   * - ``sim.plot()``
     - A 2 x 3 overview of the six panels that follow. Returns
       ``(fig, axes)``.
   * - ``sim.plot_count_rates()``
     - Bar chart of the count-rate contributors (planet, zodi, exozodi,
       speckle, dark current).
   * - ``sim.plot_snr_vs_time()``
     - SNR as a function of integration time; see the sweeps below.
   * - ``sim.plot_bandpass()`` / ``sim.sensor.plot_bandpass()``
     - The sensor's optical bandpass (throughput against wavelength).
   * - ``sim.plot_aperture()`` / ``sim.sensor.plot_aperture()``
     - The photometric aperture drawn over a pixel-integrated Airy PSF.
   * - ``sim.plot_offaxis_throughput()`` / ``sim.coronagraph.plot_offaxis_throughput()``
     - Focal-plane mask throughput against separation, with the current
       separation marked.
   * - ``sim.plot_spectra()`` / ``sim.scene.plot_spectra()``
     - The scene-element spectra (star, planet and zodi by default).

The overview
------------

.. plot::
   :context: close-figs

   fig, axes = sim.plot()

Single panels
-------------

Each panel is its own method. The count-rate budget and the aperture
footprint:

.. plot::
   :context: close-figs

   fig, ax = sim.plot_count_rates()

.. plot::
   :context: close-figs

   fig, ax = sim.sensor.plot_aperture()

Parameter sweeps
----------------

``plot_snr_vs_time`` takes ``sweep=``, a one-entry dictionary naming any
parameter you could pass to :meth:`~esc_etc.Simulation.update` and the values
to try. One curve is drawn per value and the original value is put back:

.. plot::
   :context: close-figs

   fig, ax = sim.plot_snr_vs_time(sweep={"coronagraph__raw_dh_contrast": [1e-7, 1e-8, 1e-9]})

The same works for any other parameter, for example
``sweep={"coronagraph__ppgain": [5, 10, 20, 50]}`` or
``sweep={"scene__zodi__mag": [22.5, 20]}``.

Several curves on one axis
--------------------------

``plot_snr_vs_time``, ``plot_bandpass`` and ``plot_offaxis_throughput`` take
``label=``; with ``ax=`` that gives a legend without touching the lines:

.. plot::
   :context: close-figs

   import matplotlib.pyplot as plt

   fig, ax = plt.subplots()
   for ft in [10, 100, 1000]:
       sim.plot_snr_vs_time(frame_time=ft, ax=ax, label=f"frame time {ft} s")

.. plot::
   :context: close-figs

   fig, ax = plt.subplots()
   Simulation.from_default(filter="F630N", lifetime="eol").plot_bandpass(ax=ax, label="EOL")
   Simulation.from_default(filter="F630N", lifetime="bol").plot_bandpass(ax=ax, label="BOL")

The functions behind the methods
--------------------------------

The methods call the functions in :mod:`esc_etc.plotting`, which also accept
raw arrays instead of a simulation (``rates`` with a ``sensor``,
``total_times`` with ``snrs``, ``wavelength`` with ``throughput``, and so
on). See the :doc:`../api/plotting` reference for the signatures.

.. tip::

   When generating many figures in a loop, close the ones you do not keep
   with ``plt.close(fig)`` to avoid accumulating open figures.

The house style
---------------

The same style is available for your own plots:

.. code-block:: python

   from esc_etc import lazuli_style, use_lazuli_style

   use_lazuli_style()             # apply globally to the current session

   with lazuli_style():           # or scope it to a block
       ...                        # your plotting code

The exported colour tokens ``TEAL``, ``RED``, ``AMBER``, ``BLUE``, ``GREEN``,
``DARKBLUE`` and the ``LAZULI_COLORS`` sequence are the palette the methods
use.
