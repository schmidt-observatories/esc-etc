Coronagraph and contrast
========================

The :class:`~esc_etc.Coronagraph` owns the coronagraph-specific physics. It has
three mutable knobs and a configuration-derived throughput curve.

The three knobs
---------------

.. list-table::
   :header-rows: 1
   :widths: 24 76

   * - Parameter
     - Meaning
   * - ``raw_dh_contrast``
     - The raw dark-hole contrast (e.g. ``1e-8``). It sets the residual speckle
       level: the speckle count rate is the host rate scaled by
       :meth:`~esc_etc.Coronagraph.speckle_scale`, i.e.
       :math:`10^{-0.4\,\Delta m}` with
       :math:`\Delta m = -2.5\log_{10}(\text{raw\_dh\_contrast})`.
   * - ``ppgain``
     - The post-processing gain. It suppresses the systematic speckle floor by a
       factor :meth:`~esc_etc.Coronagraph.noise_floor_factor` :math:`= 1/\text{ppgain}`.
   * - ``separation``
     - The planet's angular separation (arcsec). It selects the off-axis
       throughput from the FPM curve and is the separation at which the planet is
       observed.

The off-axis (FPM) throughput
-----------------------------

:meth:`~esc_etc.Coronagraph.off_axis_throughput` converts a separation in arcsec
to units of :math:`\lambda/D` (using the primary filter wavelength and aperture
diameter) and looks up the focal-plane-mask transmission from the curve loaded
out of the instrument configuration:

.. code-block:: python

   sim.coronagraph.off_axis_throughput()        # at the current separation
   sim.coronagraph.off_axis_throughput(0.6)     # at 0.6 arcsec

.. note::

   This throughput :math:`k` is applied as a **flat scalar to every count rate**
   in :meth:`~esc_etc.Simulation.count_rate_components` — planet, speckle, zodi,
   exozodi, and the reported host rate are all multiplied by :math:`k`.

Sweeping the knobs
------------------

Update any knob and recompute. For example, to see how SNR improves with more
aggressive post-processing or at a wider separation:

.. code-block:: python

   import astropy.units as u

   for ppg in (5, 10, 20, 50):
       sim.update(coronagraph__ppgain=ppg)
       print(ppg, sim.get_snr(total_time=3600 * u.s, frame_time=100 * u.s)["snr"])

   sim.reset()

The :func:`~esc_etc.plot_offaxis_throughput` helper plots the full throughput-vs-
separation curve (see :doc:`plotting`).
