Scenes and sources
==================

A :class:`~esc_etc.Scene` bundles the four observable elements of a
coronagraphic observation, each a :class:`~esc_etc.SceneElement`:

- **star** — the host star, normalized to ``hoststarmag``.
- **planet** — specified as a delta-magnitude (``planetdeltamag``) relative to
  the host; the planet count rate is the host rate scaled by
  :math:`10^{-0.4\,\Delta m}`.
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
       hoststarmag=-0.353,    # host-star magnitude
       planetdeltamag=20.0,   # planet is 20 mag fainter than the host
       bg_flux=22.5,          # zodi surface brightness (mag / arcsec^2)
       exobg_flux=21.0,       # exozodi surface brightness (mag / arcsec^2)
       mag_system="vega",     # "vega" (default) or "AB"
   )

The resulting ``scene`` exposes its elements as ``scene.star``,
``scene.planet``, ``scene.zodi``, and ``scene.exozodi``.

Magnitude systems
-----------------

Magnitudes are interpreted in the Vega system by default; pass
``mag_system="AB"`` to use AB magnitudes instead. The same choice is honored per
element when the count rates are normalized in
:meth:`~esc_etc.Simulation.count_rate_components`.

Updating scene elements
-----------------------

Each :class:`~esc_etc.SceneElement` is a meta holder with mutable parameters
``mag``, ``mag_system``, and ``deltamag``, so you can change magnitudes in place
and recompute. Through a :class:`~esc_etc.Simulation`, route updates with the
``scene__`` prefix (the scene element name is the next segment):

.. code-block:: python

   sim.update(scene__star__mag=-0.2)         # brighter host
   sim.update(scene__planet__deltamag=18.0)  # brighter planet (smaller delta-mag)
   sim.reset()

If you hold a bare :class:`~esc_etc.Scene` instead, drop the ``scene__`` prefix
(``scene.update(star__mag=-0.2)``).
