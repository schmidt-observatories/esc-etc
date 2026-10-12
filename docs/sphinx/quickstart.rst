Quick start
===========

Every snippet on this page uses the public top-level API of ``esc_etc``.
Times given as plain numbers are seconds; astropy quantities in any time unit
work too.

The mental model
----------------

A calculation is built from four pieces, combined into a
:class:`~esc_etc.Simulation`:

.. code-block:: text

   Telescope   (aperture, surface, filter)   ─┐
   Sensor      (detector + optical throughput) ├──►  Simulation  ──►  SNR / int. time / saturation
   Scene       (star, planet, zodi, exozodi)   │
   Coronagraph (contrast, ppgain, separation)  ─┘

- The :class:`~esc_etc.Telescope` holds the collecting area, the focal
  geometry, the filter's central wavelength and the resolution element
  (``resel``). The resel is the area of one diffraction-limited PSF core, a
  disc of diameter :math:`\lambda/D` on the sky, and is the default
  photometric aperture.
- The :class:`~esc_etc.Sensor` couples the detector (read noise, dark current,
  gain, well depth) with the optical bandpass and the photometric aperture
  every noise term uses.
- The :class:`~esc_etc.Scene` holds the host star, the planet (given as a
  magnitude difference from the host) and the zodiacal and exozodiacal
  backgrounds, each a :class:`~esc_etc.SceneElement`.
- The :class:`~esc_etc.Coronagraph` holds the raw dark-hole contrast, the
  post-processing gain, the planet separation and the focal-plane mask
  throughput curve. :doc:`user_guide/coronagraph` defines these terms.

1. Build a simulation from the defaults
---------------------------------------

:meth:`Simulation.from_default <esc_etc.Simulation.from_default>` assembles
all four components from the bundled configuration of the Lazuli 3 m
telescope and the ESC:

.. code-block:: python

   from esc_etc import Simulation

   sim = Simulation.from_default(
       hoststarmag=-0.353,    # host-star Vega magnitude in the ESC band
       planetdeltamag=20.0,   # planet 20 mag fainter than the host: a flux ratio of 1e-8
       contrast=1e-8,         # raw dark-hole contrast (coronagraph.raw_dh_contrast)
       ppgain=10,             # assumed post-processing gain on the residual starlight
       separation=0.4,        # planet separation in arcsec, about 9 lambda/D at 630 nm
   )

With these numbers the planet sits exactly at the raw contrast level, so the
residual starlight in the aperture is as bright as the planet. ``contrast=``
here sets the same quantity that the rest of the documentation calls
``raw_dh_contrast``. :doc:`user_guide/concepts` shows how to build each
component yourself and assemble them with
:meth:`Simulation.from_components <esc_etc.Simulation.from_components>`.

2. Compute signal-to-noise
--------------------------

:meth:`~esc_etc.Simulation.get_snr` returns a dictionary. The signal-to-noise
itself is under the ``"snr"`` key:

.. code-block:: python

   import astropy.units as u

   result = sim.get_snr(total_time=3600 * u.s, frame_time=100 * u.s)
   result = sim.get_snr(3600, 100)               # plain numbers are seconds
   result["snr"]        # signal-to-noise ratio, about 9.87 here
   result["signal_e"]   # planet electrons accumulated in total_time
   result["noise_e"]    # total noise (electrons)
   result["M"]          # speckle rate divided by ppgain: the post-processing noise floor

``total_time`` is the on-target integration and ``frame_time`` is how often
the detector is read out. The number of reads is ``ceil(total_time /
frame_time)``, never fewer than one, and sets how much read noise accumulates.
Saturation bounds the frame time from above, read noise from below; see
:doc:`user_guide/saturation`. The full budget is in :doc:`user_guide/snr`.

3. Invert: integration time for a target SNR
--------------------------------------------

.. code-block:: python

   inv = sim.get_int_time_for_snr(snr=5, frame_time=100 * u.s)
   inv["int_time"]             # whole-frame integration time that reaches SNR = 5
   inv["int_time_continuous"]  # unrounded closed-form value
   inv["noise_terms"]          # [dark, read, zodi, exozodi, speckle, reference] rates

The speckle noise floor grows with time exactly as the signal does, so each
configuration has a maximum reachable signal-to-noise: ``ppgain`` times the
planet-to-speckle rate ratio, which is 10 for the defaults above. A target
above that limit comes back as ``nan``.

4. Check saturation
-------------------

.. code-block:: python

   sim.saturation_time()        # frame time (s) at which the brightest pixel fills the well
   sim.is_saturated(100)        # True / False for a 100 s frame

The pixel in question is the brightest one in the planet's aperture, where
the starlight has been suppressed to the raw contrast. The stellar core behind
the focal-plane mask (the occulting spot that blocks the star) is not
modelled, so for a bright host the detector-safe frame time can be much
shorter; see :doc:`user_guide/saturation`.

5. Change parameters and recompute
----------------------------------

Every component's tunable parameters can be changed in place with
:meth:`~esc_etc.Simulation.update`, using ``child__param`` double-underscore
syntax, and recomputed. :meth:`~esc_etc.Simulation.reset` restores the
original values.

.. code-block:: python

   sim.update(coronagraph__separation=0.6)   # wider separation
   sim.update(coronagraph__ppgain=20)        # twice the assumed post-processing gain
   sim.update(sensor__read_noise=5)          # quieter detector; plain numbers are in the sensor's own units
   sim.update(sensor__aperture="optimal")    # a different photometric aperture
   sim.get_snr(3600, 100)["snr"]

   sim.reset()                               # back to the initial configuration

To use one of the ESC filters instead of the generic configuration bandpass,
build the simulation with ``filter=`` (a key of :data:`esc_etc.FILTERS`) and
``lifetime="eol"`` for the end-of-life throughput or ``"bol"`` for beginning
of life:

.. code-block:: python

   sim = Simulation.from_default(filter="F630N", lifetime="eol")

6. Plot the results
-------------------

Every standard plot is a method; each accepts ``ax=`` and returns ``(fig, ax)``:

.. code-block:: python

   fig, axes = sim.plot()                 # 2 x 3 overview
   fig, ax = sim.plot_count_rates()       # bar chart of count-rate contributors
   fig, ax = sim.plot_snr_vs_time()       # SNR vs integration time
   fig, ax = sim.plot_snr_vs_time(sweep={"coronagraph__ppgain": [1, 10, 100]})

The plots apply the packaged style through a context manager, so your own
matplotlib settings are untouched. :func:`~esc_etc.use_lazuli_style` applies
the same style to your own figures. See :doc:`user_guide/plotting`.

Where to go next
----------------

- :doc:`user_guide/index` for the physics behind each piece.
- :doc:`tutorials` for the four runnable notebooks.
- :doc:`api/index` for the full auto-generated API reference.
