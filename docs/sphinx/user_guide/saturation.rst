Saturation
==========

``esc-etc`` reports saturation as a *frame time*: the longest single frame you
can read out before the detector well fills. Because the ESC noise model reads
an integration out in frames of duration ``frame_time`` (see :doc:`snr`),
saturation is a constraint on that frame time, not on the total integration.

The saturation time
-------------------

:meth:`~esc_etc.Simulation.saturation_time` divides the sensor well depth by the
per-pixel electron rate:

.. math::

   t_\mathrm{sat} = \frac{W}{\left(R_\mathrm{source} + R_\mathrm{zodi} +
   R_\mathrm{speckle} + R_\mathrm{exozodi}\right) / N_\mathrm{pix}}

where :math:`W` is :attr:`Sensor.well_depth <esc_etc.Sensor.well_depth>` and
:math:`N_\mathrm{pix}` is :attr:`Sensor.num_psf_pixels
<esc_etc.Sensor.num_psf_pixels>`. The rates come from
:meth:`~esc_etc.Simulation.count_rate_components`:

.. code-block:: python

   import astropy.units as u

   sim.saturation_time()         # seconds
   sim.is_saturated(100 * u.s)   # True / False for a 100 s frame

:meth:`~esc_etc.Simulation.is_saturated` is the direct comparison
``frame_time > saturation_time()``.

.. note::

   The host star is deliberately **excluded** from the per-pixel sum. Only the
   planet, zodi, speckle, and exozodi rates contribute. This matches the legacy
   ``calc_saturation_time`` in
   :class:`~esc_etc.ExposureTimeSNRCalculatorESC.ExposureTimeSNRCalculatorESC`,
   and reflects the fact that the quantity of interest is the accumulation in
   the dark hole, not at the (occulted) star's position.

   All rates are already scaled by the flat FPM throughput
   ``coronagraph.off_axis_throughput``, so the saturation time refers to the
   post-coronagraph focal plane.

What sets the per-pixel rate
----------------------------

Two knobs move :math:`t_\mathrm{sat}` for a fixed scene:

**Well depth.** :attr:`~esc_etc.Sensor.well_depth` is a mutable sensor
parameter, so a different gain setting can be explored in place:

.. code-block:: python

   sim.update(sensor__well_depth=60000 * u.electron)
   sim.saturation_time()
   sim.reset()

**PSF pixel count.** :meth:`Sensor.calc_psf <esc_etc.Sensor.calc_psf>` runs at
construction and sets ``num_psf_pixels`` from the diffraction-limited spot
diameter :math:`2 \times 1.22\,\lambda\,F_\#` at the bandpass peak, divided by
the pixel size. The default ``approx_type="sq"`` counts the enclosing
:math:`n \times n` square; passing a circular approximation counts the inscribed
disk instead, which is roughly 20 % fewer pixels and therefore a *shorter*
saturation time for the same total rate:

.. code-block:: python

   sim.sensor.calc_psf("circle")   # recompute with a circular aperture
   sim.saturation_time()

Choosing a frame time
---------------------

Saturation pushes ``frame_time`` down; read noise pushes it up. The read-noise
term in the noise budget is
:math:`\sigma_\mathrm{read}^2 \, N_\mathrm{pix} \, (t_\mathrm{total} /
t_\mathrm{frame})` — it grows with the *number of reads*, so splitting a long
integration into many short frames to dodge saturation costs SNR.

A workable frame time therefore sits just under :math:`t_\mathrm{sat}`:

.. code-block:: python

   frame_time = 0.8 * sim.saturation_time()
   result = sim.get_snr(total_time=3600 * u.s, frame_time=frame_time)

.. tip::

   The total integration time is unconstrained by saturation — only the
   individual frame is. If ``saturation_time()`` comes back shorter than a
   practical readout cadence, the fix is a shallower scene (fainter host,
   better contrast) or a deeper well, not a shorter total exposure.

See :doc:`../notebooks/04_integration_time_snr_saturation` for a worked example
that sweeps frame time against both saturation and SNR.
