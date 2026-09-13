Quick start
===========

This page walks through the core workflow in a few minutes. Every snippet
below uses only the public top-level API exported from ``esc_etc``.

The mental model
----------------

A calculation is built from four pieces, combined into a
:class:`~esc_etc.Simulation`:

.. code-block:: text

   Telescope   (aperture, surface, filter)   ─┐
   Sensor      (detector + optical throughput) ├──►  Simulation  ──►  SNR / int. time / saturation
   Scene       (star, planet, zodi, exozodi)   │
   Coronagraph (contrast, ppgain, separation)  ─┘

- A :class:`~esc_etc.Telescope` carries the collecting area, focal geometry,
  primary filter wavelength, and the resolution element (``resel``), the
  photometric extraction aperture shared by every noise term.
- A :class:`~esc_etc.Sensor` couples the detector characteristics (read noise,
  dark current, gain, well depth, number of PSF pixels) with the optical
  **bandpass**.
- A :class:`~esc_etc.Scene` holds the host **star**, the **planet** (as a
  delta-magnitude relative to the star), and the **zodi** / **exozodi** sky
  backgrounds, each a :class:`~esc_etc.SceneElement`.
- A :class:`~esc_etc.Coronagraph` owns the raw dark-hole contrast, the
  post-processing gain, the planet separation, and the off-axis throughput.

1. Build a simulation from the defaults
---------------------------------------

The fastest path is :meth:`Simulation.from_default
<esc_etc.Simulation.from_default>`, which assembles all four components from the
bundled UASAL configuration (UA Ultramarine 3 m + ESC instrument):

.. code-block:: python

   from esc_etc import Simulation
   import astropy.units as u

   sim = Simulation.from_default(
       hoststarmag=-0.353,    # host-star Vega magnitude in the ESC band
       planetdeltamag=20.0,   # planet is 20 mag fainter than the host (ESC band)
       contrast=1e-8,         # raw dark-hole contrast
       ppgain=10,             # post-processing gain
       separation=0.4,        # planet separation (arcsec)
   )

See :doc:`user_guide/concepts` for building each component yourself with
:meth:`Simulation.from_components <esc_etc.Simulation.from_components>`.

2. Compute signal-to-noise
--------------------------

:meth:`~esc_etc.Simulation.get_snr` returns a **dictionary**. The
signal-to-noise itself is under the ``"snr"`` key:

.. code-block:: python

   result = sim.get_snr(total_time=3600 * u.s, frame_time=100 * u.s)
   result["snr"]        # signal-to-noise ratio
   result["signal_e"]   # source electrons accumulated in total_time
   result["noise_e"]    # total noise (electrons)
   result["M"]          # post-processed speckle noise-floor rate

``total_time`` is the integrated exposure; ``frame_time`` is the per-frame
read-out cadence. The number of reads is ``ceil(total_time / frame_time)``,
never fewer than one, and sets how much read noise accumulates. See
:doc:`user_guide/snr` for the full noise budget.

3. Invert: integration time for a target SNR
--------------------------------------------

.. code-block:: python

   inv = sim.get_int_time_for_snr(snr=10, frame_time=100 * u.s)
   inv["int_time"]             # whole-frame integration time to reach SNR = 10
   inv["int_time_continuous"]  # unrounded closed-form value
   inv["noise_terms"]          # per-source noise contributions

Because residual speckle imposes a noise floor, some target SNRs are
unreachable at a given contrast/ppgain; those entries come back as ``nan``.

4. Check saturation
-------------------

.. code-block:: python

   sim.saturation_time()        # frame time (s) at which the well fills
   sim.is_saturated(100 * u.s)  # True / False for a 100 s frame

5. Change parameters and recompute
----------------------------------

Every component is a "meta holder": its tunable parameters can be changed in
place with :meth:`~esc_etc.Simulation.update` using ``child__param`` double-
underscore syntax, then recomputed. :meth:`~esc_etc.Simulation.reset` restores
the original values.

.. code-block:: python

   sim.update(coronagraph__separation=0.6)   # wider separation
   sim.update(coronagraph__ppgain=20)        # more aggressive post-processing
   sim.update(sensor__read_noise=5)          # quieter detector
   sim.get_snr(total_time=3600 * u.s, frame_time=100 * u.s)["snr"]

   sim.reset()                               # back to the initial configuration

6. Plot the results
-------------------

The packaged lazuli-styled helpers each return ``(fig, ax)``:

.. code-block:: python

   from esc_etc import plot_count_rates, plot_snr_vs_time

   fig, ax = plot_count_rates(sim)   # bar chart of count-rate contributors
   fig, ax = plot_snr_vs_time(sim)   # SNR vs integration time

The style is applied internally via a context manager (no global state
mutation). Call :func:`~esc_etc.use_lazuli_style` to apply it to your own
plots. See :doc:`user_guide/plotting`.

Where to go next
----------------

- :doc:`user_guide/index` — the conceptual reference for each subsystem.
- :doc:`tutorials` — the four runnable notebooks.
- :doc:`api/index` — the full auto-generated API reference.
