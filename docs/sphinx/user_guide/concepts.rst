Concepts and architecture
=========================

The four building blocks
------------------------

.. list-table::
   :header-rows: 1
   :widths: 22 78

   * - Object
     - Role
   * - :class:`~esc_etc.Telescope`
     - The optics: primary diameter, collecting area (already reduced by the
       Lyot stop), focal ratio and length, the filter's central wavelength,
       and the resolution element ``resel``, the area of one PSF core,
       :math:`\pi(\lambda/2D)^2`.
   * - :class:`~esc_etc.Sensor`
     - The detector and the optical path to it: read noise, dark current,
       gain, well depth, the optical bandpass (mirror coatings, filter and
       detector quantum efficiency, or one of the measured ESC filter curves)
       and the photometric aperture every noise term uses, with the encircled
       energy ``ee_fraction`` it credits to a point source.
   * - :class:`~esc_etc.Scene`
     - What is on the sky: the host star, the planet (a magnitude difference
       relative to the star) and the zodiacal and exozodiacal backgrounds.
       Each is a :class:`~esc_etc.SceneElement` wrapping a ``synphot``
       spectrum and a magnitude.
   * - :class:`~esc_etc.Coronagraph`
     - The coronagraph: raw dark-hole contrast ``raw_dh_contrast``,
       post-processing gain ``ppgain``, planet ``separation`` and the
       focal-plane mask throughput curve. See :doc:`coronagraph`.

A :class:`~esc_etc.Simulation` owns one of each, plus a noise model, and
turns them into count rates, signal-to-noise and integration times. The
components are reachable as ``sim.telescope``, ``sim.sensor``, ``sim.scene``,
``sim.coronagraph`` and ``sim.noise_model``.

The photometric aperture
------------------------

Every noise term is evaluated over the same aperture, chosen with
``sensor.aperture``. The aperture sets how many detector pixels contribute
dark current and read noise, and the encircled energy sets what fraction of
a point source's light is credited to it. At the default configuration
(5.0 pixels per :math:`\lambda/D`):

.. list-table::
   :header-rows: 1
   :widths: 14 46 14 14

   * - Name
     - Geometry
     - Pixels
     - Encircled energy
   * - ``resel``
     - A disc of diameter :math:`\lambda/D`, the default
     - 19.6
     - 0.456
   * - ``optimal``
     - A disc of radius 0.7 :math:`\lambda/D`
     - 38.4
     - 0.678
   * - ``box``
     - A square of side 2.44 :math:`\lambda/D` (13 x 13 pixels), the first
       Airy dark ring
     - 169
     - 0.850
   * - ``matched``
     - A matched filter: the effective pixel count of a PSF-weighted sum,
       credited with the full flux
     - 70.5
     - 1.0

``encircled_energy`` overrides the tabulated value (it must lie in
``(0, 1]``), for instance when a measured PSF gives a different number.

Constructing a simulation
-------------------------

There are two convenience constructors:

.. code-block:: python

   from esc_etc import Simulation

   # All four components from the bundled Lazuli config (3 m telescope + ESC):
   sim = Simulation.from_default(hoststarmag=-0.353, planetdeltamag=20.0,
                                 contrast=1e-8, ppgain=10, separation=0.4,
                                 arm="arm_a")

   # From components you build yourself:
   sim = Simulation.from_components(telescope, sensor, scene, coronagraph)

``from_components`` is the way in for a custom instrument: build each piece
with its own ``from_default`` or ``from_config`` (see :doc:`../configuration`),
or construct it directly, then assemble.

The noise model
---------------

:class:`~esc_etc.Simulation` takes a ``noise_model`` argument, by default
:class:`~esc_etc.AnalyticCoronagraphNoiseModel`. Any object with the same
``snr`` and ``int_time_for_snr`` methods can be passed instead, for example an
image-based model, without changing the simulation class. See :doc:`snr`.

Inspecting and updating parameters
----------------------------------

Each component tracks its tunable parameters, and
:meth:`~esc_etc.Simulation.update` changes them with ``child__key``
double-underscore syntax, where the prefix names the component the key
belongs to:

.. code-block:: python

   sim.update(coronagraph__separation=0.6)   # coronagraph knob
   sim.update(sensor__read_noise=5)          # detector knob, in the sensor's own units
   sim.update(scene__star__mag=-0.2)         # scene element (routed via Scene)

   sim.sensor.describe()                     # print a component's tunable params
   sim.reset()                               # restore every component

Changing ``raw_dh_contrast`` rescales the speckle rate, changing ``ppgain``
moves the noise floor, and changing ``separation`` picks a new off-axis
throughput, so the next SNR call reflects the change. A value the component
refuses (``encircled_energy`` outside ``(0, 1]``, a non-positive ``ppgain``)
raises ``ValueError`` and leaves the object unchanged.

Times
-----

``total_time`` and ``frame_time`` may be astropy quantities in any time unit
or plain numbers, which are read as seconds: ``sim.get_snr(3600, 100)`` and
``sim.get_snr(1 * u.h, 100 * u.s)`` are the same call.

Count rates and the electron budget
------------------------------------

Beneath the SNR helpers, :meth:`~esc_etc.Simulation.count_rate_components`
returns a :class:`~esc_etc.CountRates` dataclass with the per-second electron
rates for the planet ``source``, the ``zodi`` and ``exozodi`` backgrounds,
the residual ``speckle`` light, and the ``host``. The host rate is what the
unocculted star would deliver through the same aperture; it is only used to
scale the speckles, which are ``raw_dh_contrast`` times the host. Every rate
has already been multiplied by the focal-plane mask throughput :math:`k`.
These feed the noise model, and are the first thing to look at when an SNR
surprises you:

.. code-block:: python

   rates = sim.count_rate_components()
   rates.source, rates.zodi, rates.exozodi, rates.speckle, rates.host
