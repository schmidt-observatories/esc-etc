Scenes and sources
==================

A :class:`~esc_etc.Scene` bundles the four things on the sky in a
coronagraphic observation, each a :class:`~esc_etc.SceneElement`:

- ``star``, the host star, normalized to ``hoststarmag``.
- ``planet``, a spectral shape normalized ``deltamag`` magnitudes fainter
  than the host in a reference band, then observed through the ESC bandpass.
  By default the shape is the host's flat spectrum and the reference band is
  the ESC band itself, so the planet rate is the host rate times
  :math:`10^{-0.4\,\Delta m}`. The planet is always defined relative to the
  host; its own ``mag`` is not used.
- ``zodi``, the local zodiacal light, a surface brightness in Johnson *V*.
  It is scattered sunlight in our own solar system and does not depend on
  the target.
- ``exozodi``, the target system's own dust, which scatters the host star's
  light. It is therefore given as a surface brightness relative to the host.

Building a scene
----------------

:func:`~esc_etc.get_scene` builds all four from magnitudes, given a telescope
for the resolution element and the bandpass:

.. code-block:: python

   from esc_etc import Telescope, get_scene

   telescope = Telescope.from_default(arm="arm_a")
   scene = get_scene(
       telescope,
       hoststarmag=-0.353,    # host-star magnitude in hoststar_band
       hoststar_band=None,    # None = ESC band; "johnson_v" for a catalog V mag
       planetdeltamag=20.0,   # planet is 20 mag fainter than the host, ESC band
       bg_flux=22.5,          # zodi surface brightness, mag / arcsec^2 in Johnson V
       exobg_flux=21.0,       # exozodi surface brightness: host + 21 mag / arcsec^2, ESC band
       mag_system="vega",     # "vega" (default) or "AB", for every magnitude above
   )

The arguments map onto the elements as follows. ``hoststarmag`` becomes
``scene.star.mag`` (in ``hoststar_band``), ``planetdeltamag`` becomes
``scene.planet.deltamag``, ``bg_flux`` becomes ``scene.zodi.mag`` and
``exobg_flux`` plus the host magnitude becomes ``scene.exozodi.mag``. The two
``*_flux`` arguments are magnitudes per square arcsecond despite their
names. :meth:`Simulation.from_default <esc_etc.Simulation.from_default>`
takes the same arguments and passes them through.

.. _planet-spectra:

Planet spectra
--------------

``planetdeltamag`` is an ESC-band magnitude difference by default, so the
planet's colour cannot change its ESC count rate: whatever the shape, it is
pinned to :math:`10^{-0.4\,\Delta m}` of the host. To model a contrast quoted
in another band, set ``deltamag_band`` to a synphot filter name or a
``SpectralElement`` and give the planet its own shape. A cool planet with a
V-band contrast of 20 mag is then much brighter than a flat one at 633 nm:

.. code-block:: python

   import astropy.units as u
   from synphot import SourceSpectrum
   from synphot.models import BlackBody1D
   from esc_etc import Simulation

   sim = Simulation.from_default(planetdeltamag=20.0)
   sim.update(scene__planet__deltamag_band="johnson_v")
   flat = sim.count_rate_components().source          # flat shape, V-band contrast

   sim.update(scene__planet__spectrum=SourceSpectrum(BlackBody1D, temperature=1000 * u.K))
   red = sim.count_rate_components().source           # about 7.5x flat at the default configuration

The normalization uses the host's ``mag_system`` (Vega or AB).

Magnitude systems
-----------------

Every magnitude carries two labels, a system and a band.

- ``mag_system`` is ``"vega"`` (default) or ``"AB"``. Anything else raises
  ``ValueError`` at construction or on ``update``.
- ``band`` is where the magnitude is quoted: ``None`` for the ESC sensor
  bandpass, a synphot filter name such as ``"johnson_v"``, or a
  ``SpectralElement``. The spectrum is normalized in that band and then
  integrated through the ESC bandpass, so a catalog *V* magnitude of a red
  star gives a different ESC count rate than the same number read as an
  ESC-band magnitude.

By default the host and exozodi are ESC-band magnitudes, the zodi surface
brightness is in Johnson *V*, and ``planetdeltamag`` is an ESC-band
magnitude difference (see :ref:`planet-spectra`).

Updating scene elements
-----------------------

Each :class:`~esc_etc.SceneElement` has the mutable parameters ``spectrum``,
``mag``, ``mag_system``, ``band``, ``deltamag`` and ``deltamag_band``, so you
can change magnitudes or spectral shapes in place and recompute. Through a
:class:`~esc_etc.Simulation`, route updates with the ``scene__`` prefix
followed by the element name:

.. code-block:: python

   sim.update(scene__star__mag=-0.2)         # brighter host
   sim.update(scene__planet__deltamag=18.0)  # brighter planet (smaller magnitude difference)
   sim.update(scene__zodi__mag=20.0)         # brighter zodiacal background
   sim.reset()

If you hold a bare :class:`~esc_etc.Scene` instead, drop the ``scene__``
prefix (``scene.update(star__mag=-0.2)``).
