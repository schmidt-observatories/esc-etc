Scenes and sources
==================

A :class:`~esc_etc.Scene` bundles the four observable elements of a
coronagraphic observation, each a :class:`~esc_etc.SceneElement`:

- **star** — the host star, normalized to ``hoststarmag``.
- **planet** — a spectral shape (``spectrum``) normalized ``deltamag``
  magnitudes fainter than the host in a reference band (``deltamag_band``),
  then observed through the ESC bandpass. The default shape is the host's flat
  spectrum and the default reference band is the ESC band itself, which reduces
  to the host rate scaled by :math:`10^{-0.4\,\Delta m}`. ``planet.mag`` is
  unused; the planet is always host + ``deltamag``.
- **zodi** — the local zodiacal-light background, normalized in Johnson *V*.
- **exozodi** — the target system's exozodiacal background.

Building a scene
----------------

:func:`~esc_etc.get_scene` builds all four from magnitudes, given a telescope
(it needs the resolution element and bandpass context):

.. code-block:: python

   from esc_etc import Telescope, get_scene

   telescope = Telescope.from_default(arm="arm_a")
   scene = get_scene(
       telescope,
       hoststarmag=-0.353,    # host-star magnitude in hoststar_band
       hoststar_band=None,    # None = ESC band; "johnson_v" for a catalog V mag
       planetdeltamag=20.0,   # planet is 20 mag fainter than the host, ESC band
       bg_flux=22.5,          # zodi surface brightness, mag / arcsec^2 in Johnson V
       exobg_flux=21.0,       # exozodi DELTA mag: host + 21 mag / arcsec^2, ESC band
       mag_system="vega",     # "vega" (default) or "AB", for every magnitude above
   )

The resulting ``scene`` exposes its elements as ``scene.star``,
``scene.planet``, ``scene.zodi``, and ``scene.exozodi``.

.. _planet-spectra:

Planet spectra
--------------

``planetdeltamag`` is an **ESC-band** delta magnitude by default, so the planet's
colour cannot change its ESC count rate: whatever the shape, it is pinned to
:math:`10^{-0.4\,\Delta m}` of the host. To model a contrast quoted in another
band, set ``deltamag_band`` to a synphot filter name or a
``SpectralElement`` and give the planet its own shape. A cool planet with a
V-band contrast of 20 mag is then much brighter than a flat one at 633 nm:

.. code-block:: python

   import astropy.units as u
   from synphot import SourceSpectrum
   from synphot.models import BlackBody1D

   sim = Simulation.from_default(planetdeltamag=20.0)
   sim.update(scene__planet__deltamag_band="johnson_v")
   flat = sim.count_rate_components().source          # flat shape, V-band contrast

   sim.update(scene__planet__spectrum=SourceSpectrum(BlackBody1D, temperature=1000 * u.K))
   red = sim.count_rate_components().source           # ~8x flat at the default configuration

The normalization is always in the host's ``mag_system`` (Vega or AB).

Magnitude systems
-----------------

Every magnitude carries two labels: a **system** and a **band**.

- ``mag_system`` is ``"vega"`` (default) or ``"AB"``. Anything else raises
  ``ValueError`` at construction or ``update``. The deprecated
  ``esc_calc_snr(..., flux_units=...)`` forwards to it.
- ``band`` is where the magnitude is quoted: ``None`` for the ESC sensor
  bandpass, a synphot filter name such as ``"johnson_v"``, or a
  ``SpectralElement``. The spectrum is normalized in that band and then
  integrated through the ESC bandpass, so a catalog *V* magnitude of a red star
  gives a different ESC count rate than the same number read as an ESC-band
  magnitude.

Defaults: the host and exozodi are ESC-band magnitudes, the zodi surface
brightness is in Johnson *V*, and ``planetdeltamag`` is an ESC-band delta
magnitude (see :ref:`planet-spectra`).

Updating scene elements
-----------------------

Each :class:`~esc_etc.SceneElement` is a meta holder with mutable parameters
``spectrum``, ``mag``, ``mag_system``, ``band``, ``deltamag``, and
``deltamag_band``, so
you can change magnitudes or spectral shapes in place
and recompute. Through a :class:`~esc_etc.Simulation`, route updates with the
``scene__`` prefix (the scene element name is the next segment):

.. code-block:: python

   sim.update(scene__star__mag=-0.2)         # brighter host
   sim.update(scene__planet__deltamag=18.0)  # brighter planet (smaller delta-mag)
   sim.reset()

If you hold a bare :class:`~esc_etc.Scene` instead, drop the ``scene__`` prefix
(``scene.update(star__mag=-0.2)``).
