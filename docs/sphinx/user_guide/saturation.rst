Saturation
==========

``esc-etc`` reports saturation as a *frame time*: the longest single frame you
can read out before the brightest dark-hole pixel fills. Because the ESC noise
model reads an integration out in frames of duration ``frame_time`` (see
:doc:`snr`), saturation is a constraint on that frame time, not on the total
integration.

The saturation time
-------------------

:meth:`~esc_etc.Simulation.saturation_time` divides the usable well by the
peak-pixel electron rate:

.. math::

   t_\mathrm{sat} = \frac{h\,W}{f_\mathrm{peak}\left(R_\mathrm{source} +
   R_\mathrm{speckle}\right) + \left(R_\mathrm{zodi} + R_\mathrm{exozodi}\right)
   / N_\mathrm{pix} + R_\mathrm{dark}}

where :math:`W` is :attr:`Sensor.well_depth <esc_etc.Sensor.well_depth>`,
:math:`h` is ``Sensor.headroom`` (the usable fraction of full well, default
0.8), :math:`f_\mathrm{peak}` is ``Sensor.peak_pixel_fraction`` (the share of a
point source's in-aperture rate that lands on its brightest pixel),
:math:`N_\mathrm{pix}` is ``Sensor.num_psf_pixels``, and :math:`R_\mathrm{dark}`
is the dark current per pixel. The rates come from
:meth:`~esc_etc.Simulation.count_rate_components`:

.. code-block:: python

   import astropy.units as u

   sim.saturation_time()         # seconds
   sim.is_saturated(100 * u.s)   # True / False for a 100 s frame

:meth:`~esc_etc.Simulation.is_saturated` is the direct comparison
``frame_time > saturation_time()``, so both use the same definition.

.. note::

   The occulted host star is **out of scope**. The quantity of interest is the
   brightest pixel in the dark-hole science region, not the stellar core behind
   the focal-plane mask. All rates are already scaled by the FPM throughput
   ``coronagraph.off_axis_throughput``.

What sets the peak-pixel rate
-----------------------------

Three sensor knobs move :math:`t_\mathrm{sat}` for a fixed scene, all mutable
through :meth:`Simulation.update <esc_etc.Simulation.update>`:

**Well depth and headroom.** ``well_depth`` follows the gain setting;
``headroom`` is a safety margin on it, not a measured linearity limit:

.. code-block:: python

   sim.update(sensor__well_depth=60000 * u.electron / u.pix, sensor__headroom=0.9)
   sim.saturation_time()
   sim.reset()

**Peak-pixel fraction.** The default is computed for an unobscured Airy pattern
at the sensor plate scale: peak intensity :math:`\pi/4` per
:math:`(\lambda/D)^2`, divided by the encircled energy inside the extraction
aperture. At the default configuration this is about 0.045 of the in-aperture
rate, versus 0.033 for the aperture mean. It ignores Lyot-stop broadening and
finite-pixel integration; when a real PSF image is available, set the fraction
from it:

.. code-block:: python

   sim.update(sensor__peak_pixel_fraction=psf_image.max() / psf_image.sum())

Choosing a frame time
---------------------

Saturation pushes ``frame_time`` down; read noise pushes it up. The read-noise
term in the noise budget is
:math:`\sigma_\mathrm{read}^2 \, N_\mathrm{pix} \, (t_\mathrm{total} /
t_\mathrm{frame})` — it grows with the *number of reads*, so splitting a long
integration into many short frames to dodge saturation costs SNR.

Because ``headroom`` already holds back part of the well, a frame time at or
just under :math:`t_\mathrm{sat}` is the natural choice:

.. code-block:: python

   frame_time = sim.saturation_time()
   result = sim.get_snr(total_time=3600 * u.s, frame_time=frame_time)

.. tip::

   The total integration time is unconstrained by saturation — only the
   individual frame is. If ``saturation_time()`` comes back shorter than a
   practical readout cadence, the fix is a shallower scene (fainter host,
   better contrast) or a deeper well, not a shorter total exposure.

See :doc:`../notebooks/04_integration_time_snr_saturation` for a worked example
that sweeps frame time against both saturation and SNR.
