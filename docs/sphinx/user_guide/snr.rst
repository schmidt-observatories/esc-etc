Signal-to-noise and integration time
====================================

The signal-to-noise calculation lives in
:class:`~esc_etc.AnalyticCoronagraphNoiseModel`, the default ``noise_model``
of a :class:`~esc_etc.Simulation`. It is an analytic photometric model that
works on the per-second electron rates returned by
:meth:`~esc_etc.Simulation.count_rate_components`, all evaluated in the same
photometric aperture of :math:`N_\mathrm{pix}` detector pixels
(``Sensor.num_psf_pixels``, see :doc:`concepts`).

.. _noise-budget:

The noise budget
----------------

For an on-target integration :math:`t` read out in frames of duration
:math:`t_\mathrm{frame}`, the signal is the planet rate times the
integration time and the noise variance, in electrons squared, is

.. math::

   \sigma^2 = \left(R_\mathrm{source} + R_\mathrm{zodi} + R_\mathrm{exozodi}
   + R_\mathrm{speckle}\right) t
   + R_\mathrm{dark}\, N_\mathrm{pix}\, t
   + \sigma_\mathrm{read}^2\, N_\mathrm{pix}\, N_\mathrm{reads}
   + \kappa^2\, \mathrm{var}_\mathrm{ref}
   + (M\, t)^2,

.. math::

   \mathrm{SNR} = \frac{R_\mathrm{source}\, t}{\sigma}.

The terms, in order:

- Photon noise of the planet, the zodiacal and exozodiacal backgrounds, and
  the residual starlight (speckles). Each is a rate times the integration
  time.
- Dark current, :math:`R_\mathrm{dark}` per pixel, over the aperture.
- Read noise, :math:`\sigma_\mathrm{read}` per pixel per read, over the
  aperture and over :math:`N_\mathrm{reads} = \lceil t / t_\mathrm{frame}
  \rceil` reads: whole frames plus one shorter final frame, and never fewer
  than one. An integration shorter than a frame is still one read.
- Reference subtraction, present only with reference differential imaging
  (RDI): the scaled random variance of the subtracted reference image,
  :math:`\kappa = 1 / (\beta\,\tau)`, where :math:`\beta` is the
  reference-to-host brightness ratio and :math:`\tau = t_\mathrm{ref} / t`
  the reference-to-science time ratio. :math:`\mathrm{var}_\mathrm{ref}`
  holds the reference's speckle (scaled by :math:`\beta`), zodi, exozodi,
  dark and read terms over :math:`t_\mathrm{ref}`. See the next section.
- The post-processed speckle floor, a systematic term with
  :math:`M = R_\mathrm{speckle} / \mathrm{ppgain}` (the coronagraph's
  :meth:`noise floor factor <esc_etc.Coronagraph.noise_floor_factor>`).
  ``ppgain`` is an assumed suppression factor for the residual speckle
  pattern; the ETC does not predict post-processing performance.

The floor term grows linearly with time, exactly as the signal does, so at
long integrations the SNR stops improving and tends to

.. math::

   \mathrm{SNR}_\mathrm{max} = \frac{R_\mathrm{source}}{M}
   = \mathrm{ppgain} \times \frac{R_\mathrm{source}}{R_\mathrm{speckle}}.

At the default configuration the planet and speckle rates are equal, so
:math:`\mathrm{SNR}_\mathrm{max}` is the ``ppgain`` of 10. The ceiling moves
with a lower ``raw_dh_contrast`` (fewer speckle photons) or a higher
``ppgain``; see :doc:`coronagraph`.

.. _rdi:

Observing strategy
------------------

``coronagraph.subtraction`` states what is assumed:

- ``"none"`` (default): one science image; the budget above without the
  reference term.
- ``"rdi"``: reference differential imaging. A reference star
  ``ref_brightness_ratio`` times brighter than the host is observed for
  ``ref_time_ratio`` times the science time, scaled to the target and
  subtracted. Roll subtraction and angular differential imaging are not
  modelled.

``total_time`` is always the on-target science time. The result also reports
``science_time``, ``charged_time`` (the total telescope time, science plus
reference for RDI) and ``reference_noise_e``, the reference's contribution
in electrons:

.. code-block:: python

   sim.update(coronagraph__subtraction="rdi",
              coronagraph__ref_brightness_ratio=5.0,   # reference 5x brighter
              coronagraph__ref_time_ratio=0.5)         # observed for half the time
   r = sim.get_snr(total_time=3600, frame_time=100)
   r["reference_noise_e"], r["charged_time"]          # -> ..., 5400 s

Computing SNR
-------------

.. code-block:: python

   result = sim.get_snr(total_time=3600, frame_time=100)
   result["snr"]        # signal-to-noise ratio
   result["signal_e"]   # planet electrons in total_time
   result["noise_e"]    # total noise (electrons)
   result["M"]          # post-processed speckle floor rate
   result["reference_noise_e"], result["science_time"], result["charged_time"]

Inverting for integration time
------------------------------

:meth:`~esc_etc.Simulation.get_int_time_for_snr` solves the same expression
for the integration time needed to reach a target SNR at a given
``frame_time``:

.. code-block:: python

   inv = sim.get_int_time_for_snr(snr=10, frame_time=100)
   inv["int_time"]             # whole frames: the shortest realizable schedule
   inv["int_time_continuous"]  # closed-form inversion with fractional reads
   inv["noise_terms"]          # [dark, read, zodi, exozodi, speckle, reference] rates

``int_time`` rounds the closed-form solution up to a whole number of frames,
so it is always achievable and meets the target SNR; ``int_time_continuous``
is the unrounded value. Non-positive times, target SNRs or ``ppgain``, and a
negative contrast, raise ``ValueError``; a ``frame_time`` above
:meth:`~esc_etc.Simulation.saturation_time` emits a warning.

.. important::

   A target SNR above :math:`\mathrm{SNR}_\mathrm{max}` cannot be reached by
   integrating longer; those entries come back as ``nan``. Lower
   ``raw_dh_contrast`` or raise ``ppgain`` to lift the ceiling.

Saturation
----------

``frame_time`` is bounded from above by detector saturation and from below by
read noise, which grows with the number of reads. :doc:`saturation` explains
how :meth:`~esc_etc.Simulation.saturation_time` and
:meth:`~esc_etc.Simulation.is_saturated` bracket that choice:

.. code-block:: python

   sim.saturation_time()         # seconds
   sim.is_saturated(100)         # True / False

Swapping the noise model
------------------------

The noise model is a constructor argument, so you can pass your own object
with ``snr`` and ``int_time_for_snr`` methods (for instance an image-based
model) through :meth:`Simulation.from_components
<esc_etc.Simulation.from_components>`.
