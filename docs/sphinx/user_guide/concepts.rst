Concepts and architecture
=========================

This page describes the objects that make up a calculation and how they relate.

The four building blocks
------------------------

.. list-table::
   :header-rows: 1
   :widths: 22 78

   * - Object
     - Role
   * - :class:`~esc_etc.Telescope`
     - The optics: primary diameter, throughput surface / collecting area, focal
       ratio and length, the primary-filter wavelength, and the resolution
       element (``resel``, :math:`\pi(\lambda/2D)^2`), the default photometric
       aperture.
   * - :class:`~esc_etc.Sensor`
     - The detector + optical path: read noise, dark current, gain, well depth,
       the optical **bandpass** (mirror coatings, filter and detector QE, or a
       measured ESC filter curve), and the photometric ``aperture`` every noise
       term uses (``"resel"`` by default, or ``"optimal"``, ``"box"``,
       ``"matched"``) with the encircled energy ``ee_fraction`` it credits to a
       point source.
   * - :class:`~esc_etc.Scene`
     - What is on the sky: the host **star**, the **planet** (a delta-magnitude
       relative to the star), and the **zodi** / **exozodi** sky backgrounds.
       Each is a :class:`~esc_etc.SceneElement` wrapping a ``synphot`` spectrum
       and a magnitude.
   * - :class:`~esc_etc.Coronagraph`
     - The coronagraph: raw dark-hole contrast (``raw_dh_contrast``),
       post-processing gain (``ppgain``), planet ``separation``, and the
       off-axis (FPM) :math:`\lambda/D` throughput curve.

A :class:`~esc_etc.Simulation` owns one of each, plus a pluggable noise model,
and turns them into photometry.

Constructing a simulation
--------------------------

There are two convenience constructors:

.. code-block:: python

   from esc_etc import Simulation

   # All four components from the bundled UASAL config (UM 3 m + ESC):
   sim = Simulation.from_default(hoststarmag=-0.353, planetdeltamag=20.0,
                                 contrast=1e-8, ppgain=10, separation=0.4,
                                 arm="arm_a")

   # From components you build yourself:
   sim = Simulation.from_components(telescope, sensor, scene, coronagraph)

``from_components`` is the seam for custom instruments: build each piece with its
own ``from_default`` / ``from_config`` (see :doc:`../configuration`), or
construct them directly, then assemble.

The pluggable noise model
-------------------------

:class:`~esc_etc.Simulation` accepts a ``noise_model`` argument. The default is
:class:`~esc_etc.AnalyticCoronagraphNoiseModel`; any object implementing the same
``snr`` / ``int_time_for_snr`` interface can be swapped in — for example a future
2-D PSF image model — without subclassing the simulation engine. See
:doc:`snr`.

Inspecting and updating parameters
----------------------------------

Every component is a "meta holder" (it subclasses the internal
``_MetaHolder_``). Its tunable parameters are tracked in ``_mutable_parameters``
and changed with :meth:`~esc_etc.Simulation.update` using ``child__key``
double-underscore syntax — the child prefix selects which sub-object the key
belongs to:

.. code-block:: python

   sim.update(coronagraph__separation=0.6)   # coronagraph knob
   sim.update(sensor__read_noise=5)          # detector knob
   sim.update(scene__star__mag=-0.2)         # scene element (routed via Scene)

   sim.sensor.describe()                     # print a component's tunable params
   sim.reset()                               # restore every component

Updating a coronagraph parameter such as ``raw_dh_contrast``, ``ppgain``, or
``separation`` changes the speckle scaling, the noise floor, and the off-axis
throughput respectively, so the next SNR call reflects the change. A value the
component refuses (``encircled_energy`` outside ``(0, 1]``, a non-positive
``ppgain``) raises ``ValueError`` and leaves the object unchanged.

Times
-----

``total_time`` and ``frame_time`` may be astropy quantities in any time unit
or plain numbers, which are read as seconds: ``sim.get_snr(3600, 100)`` and
``sim.get_snr(1 * u.h, 100 * u.s)`` are the same call.

Count rates and the electron budget
------------------------------------

Beneath the SNR helpers, :meth:`~esc_etc.Simulation.count_rate_components`
returns a :class:`~esc_etc.CountRates` dataclass with the per-second electron
rates for the planet ``source``, ``zodi``, ``exozodi``, residual ``speckle``,
and the (post-FPM) ``host``. Every rate has already been multiplied by the flat
off-axis FPM throughput :math:`k`. These feed the noise model and are handy for
debugging a surprising SNR:

.. code-block:: python

   rates = sim.count_rate_components()
   rates.source, rates.zodi, rates.exozodi, rates.speckle, rates.host
