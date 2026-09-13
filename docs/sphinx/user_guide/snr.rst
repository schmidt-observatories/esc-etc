Signal-to-noise and integration time
====================================

The signal-to-noise calculation lives in
:class:`~esc_etc.AnalyticCoronagraphNoiseModel`, the default ``noise_model`` on a
:class:`~esc_etc.Simulation`. It is an analytic, photometric model — extracted
from the original ``calc_SNR`` / ``calc_int_time`` routines — operating on the
per-second electron rates returned by
:meth:`~esc_etc.Simulation.count_rate_components`.

The noise budget
----------------

For an integration ``total_time`` read out in frames of duration ``frame_time``,
the total noise (in electrons) combines:

- **Planet shot noise** — :math:`R_\mathrm{source}\,t`.
- **Zodi and exozodi shot noise** — :math:`R_\mathrm{zodi}\,t` and
  :math:`R_\mathrm{exozodi}\,t`.
- **Speckle shot noise** — :math:`R_\mathrm{speckle}\,t`.
- **Dark current** — :math:`R_\mathrm{dark}\,t \times N_\mathrm{pix}`, summed
  over the PSF pixels.
- **Read noise** — :math:`\sigma_\mathrm{read}^2 \, N_\mathrm{pix} \,
  N_\mathrm{reads}`, with :math:`N_\mathrm{reads} = \lceil t / t_\mathrm{frame}
  \rceil`: whole frames plus one shorter final frame, and never fewer than one
  read. An integration shorter than a frame is still one read.
- **Post-processed speckle floor** — a systematic term
  :math:`(M\,t)^2`, where :math:`M = R_\mathrm{speckle} \times` the
  coronagraph's :meth:`noise floor factor <esc_etc.Coronagraph.noise_floor_factor>`
  (:math:`1/\mathrm{ppgain}`).

The signal is the planet rate times the integration time, and the SNR is their
ratio.

Computing SNR
-------------

.. code-block:: python

   import astropy.units as u

   result = sim.get_snr(total_time=3600 * u.s, frame_time=100 * u.s)
   result["snr"]        # signal-to-noise ratio
   result["signal_e"]   # source electrons in total_time
   result["noise_e"]    # total noise (electrons)
   result["M"]          # post-processed speckle floor rate

Inverting for integration time
------------------------------

:meth:`~esc_etc.Simulation.get_int_time_for_snr` solves the same expression for
the integration time needed to reach a target SNR at a given ``frame_time``:

.. code-block:: python

   inv = sim.get_int_time_for_snr(snr=10, frame_time=100 * u.s)
   inv["int_time"]             # whole frames: shortest realizable schedule
   inv["int_time_continuous"]  # closed-form inversion with fractional reads
   inv["noise_terms"]          # [dark, read, zodi, exozodi, speckle] contributions

``int_time`` rounds the closed-form solution up to a whole number of frames, so
it is always achievable and meets the target SNR; ``int_time_continuous`` is the
unrounded value. Non-positive times, target SNRs, ``ppgain`` or negative
contrast raise ``ValueError``; a ``frame_time`` above
:meth:`~esc_etc.Simulation.saturation_time` emits a warning.

.. important::

   The post-processed speckle floor sets a hard ceiling on achievable SNR for a
   given ``raw_dh_contrast`` and ``ppgain``: once the target SNR exceeds what the
   floor allows, no finite integration time reaches it, and those entries are
   returned as ``nan``. Improve the contrast or the post-processing gain (see
   :doc:`coronagraph`) to push the ceiling up.

Saturation
----------

``frame_time`` is bounded from above by detector saturation and from below by
read noise, which grows with the number of reads. See :doc:`saturation` for how
:meth:`~esc_etc.Simulation.saturation_time` and
:meth:`~esc_etc.Simulation.is_saturated` bracket that choice:

.. code-block:: python

   sim.saturation_time()         # seconds
   sim.is_saturated(100 * u.s)   # True / False

Swapping the noise model
------------------------

Because the noise model is a constructor argument, you can supply your own
implementation of the ``snr`` / ``int_time_for_snr`` interface (for instance a
2-D PSF image-based model) and pass it through
:meth:`Simulation.from_components <esc_etc.Simulation.from_components>` without
touching the rest of the engine.
