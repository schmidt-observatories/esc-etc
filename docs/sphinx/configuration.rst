Configuration and filters
=========================

Instrument and telescope properties (mirrors, optics, coating throughputs,
filters, detector tables) are not hard-coded in ``esc_etc``. They come from
two sets of TOML files and support data bundled under ``esc_etc/data/lazuli/``:
``telescope`` for the Lazuli 3 m telescope and ``esc`` for the ESC instrument.
Both are snapshots of configuration packages maintained by the University of
Arizona Space Astrophysics Laboratory (UASAL), `config_um
<https://github.com/uasal/config_um>`_ and `config_um_esc
<https://github.com/uasal/config_um_esc>`_ ("UM" is the UA code name for
Lazuli). Because the copies ship inside ``esc_etc``, a plain ``pip install``
needs no git access.

The default instrument
----------------------

:meth:`Simulation.from_default <esc_etc.Simulation.from_default>` assembles
the telescope, sensor, scene and coronagraph from the bundled files for one
optical arm of the ESC. The instrument has two arms, each with its own optical
train and filter wheel; the default is ``"arm_a"``.

.. code-block:: python

   from esc_etc import Simulation

   sim = Simulation.from_default(arm="arm_a")
   sim = Simulation.from_default(filter="F630N", lifetime="eol")

``filter`` picks the ESC filter whose measured end-to-end throughput curve
is the sensor bandpass; the telescope's design wavelength follows it. The
default is :data:`esc_etc.DEFAULT_FILTER` (``"F630N"``, slot R2), so the two
calls above build the same simulation. ``lifetime`` selects the ``"eol"``
curve set (end of life, the default) or ``"bol"`` (beginning of life); any
other value raises ``ValueError``. ``filter=None`` is the legacy option: the
generic box-filter chain assembled from the configuration files, which is
wider and a little more transmissive than any real filter and has no
``lifetime`` variants.

The ESC filters
---------------

A filter is named either by its wheel slot or by its designation; both are
keys of :data:`esc_etc.FILTERS`. The N filters have a 2% bandwidth, the W
filters 10%.

.. list-table::
   :header-rows: 1
   :widths: 10 16 14 20 40

   * - Slot
     - Designation
     - Arm
     - Central wavelength
     - Bandwidth
   * - ``B1``
     - ``F400N``
     - blue
     - 400.0 nm
     - 2%
   * - ``B2``
     - ``F450N``
     - blue
     - 450.0 nm
     - 2%
   * - ``B3``
     - ``F475N``
     - blue
     - 475.0 nm
     - 2%
   * - ``B4``
     - ``F450W``
     - blue
     - 450.0 nm
     - 10%
   * - ``B5``
     - ``F425N``
     - blue
     - 425.0 nm
     - 2%
   * - ``B6``
     - ``F425W``
     - blue
     - 425.0 nm
     - 10%
   * - ``R1``
     - ``F620N``
     - red
     - 620.0 nm
     - 2%
   * - ``R2``
     - ``F630N``
     - red
     - 630.0 nm
     - 2%
   * - ``R3``
     - ``F659W``
     - red
     - 659.0 nm
     - 10%
   * - ``R4``
     - ``F685N``
     - red
     - 685.0 nm
     - 2%
   * - ``R5``
     - ``F725.9N``
     - red
     - 725.9 nm
     - 2%
   * - ``R6``
     - ``F656N``
     - red
     - 656.0 nm
     - 2%

The curves are the Lazuli throughput budget of 2026-03-25: telescope plus
ESC, including detector quantum efficiency and a
polarization factor of 0.5, and at end of life also contamination and the
budget reserves. They exclude the vortex off-axis throughput and the Lyot stop
area, which ``esc_etc`` applies itself. ``DATA_SOURCES.md`` in the repository
records the provenance of every bundled file.

Building the components yourself
--------------------------------

Each component has its own default constructor, keyed on the same ``arm`` and
``filter``. The telescope and the sensor must be built for the same filter;
mixing them raises ``ValueError``:

.. code-block:: python

   from esc_etc import Telescope, Sensor, Coronagraph, get_scene

   telescope   = Telescope.from_default(arm="arm_a", filter="F630N")
   sensor      = Sensor.from_default(telescope, arm="arm_a", filter="F630N")
   scene       = get_scene(telescope, hoststarmag=-0.353, planetdeltamag=20.0)
   coronagraph = Coronagraph.from_default(telescope, raw_dh_contrast=1e-8,
                                          ppgain=10, separation=0.4)

Supplying your own configuration
--------------------------------

The ``from_config`` constructors take an already-loaded configuration
dictionary and a support-data path, so you can point the ETC at a custom
instrument that follows the same layout as the bundled snapshot, which is
loaded the same way:

.. code-block:: python

   from esc_etc import uasal_config

   coronagraph = Coronagraph.from_config(
       instrument_config=uasal_config.load_config_values(uasal_config.INSTRUMENT),
       instrument_support_path=uasal_config.get_data_path(uasal_config.INSTRUMENT),
       telescope=telescope,
       raw_dh_contrast=1e-8, ppgain=10, separation=0.4, arm="arm_a",
   )

See :meth:`Sensor.from_config <esc_etc.Sensor.from_config>`,
:meth:`Telescope.from_config <esc_etc.Telescope.from_config>` and
:meth:`Coronagraph.from_config <esc_etc.Coronagraph.from_config>` for the
exact signatures.

Overriding parameters at runtime
--------------------------------

You do not need to edit configuration files to explore parameter changes.
Every component exposes its tunable parameters through
:meth:`~esc_etc.Simulation.update` with ``child__key`` syntax, and
:meth:`~esc_etc.Simulation.reset` reverts the whole simulation:

.. code-block:: python

   sim.update(coronagraph__separation=0.6)
   sim.update(coronagraph__raw_dh_contrast=5e-9, coronagraph__ppgain=20)
   sim.update(sensor__aperture="optimal")
   sim.reset()

Call ``describe()`` on a component (``sim.sensor.describe()``) to print its
tunable parameters.

What is in the bundled snapshot
-------------------------------

.. list-table::
   :header-rows: 1
   :widths: 40 60

   * - Path under ``esc_etc/data/``
     - Contents
   * - ``lazuli/telescope/configs/*.toml``
     - Telescope geometry and coatings (M1 to M4), observatory pointing and
       jitter, zodiacal-light defaults.
   * - ``lazuli/telescope/support_data/``
     - Zodiacal-light spectral template and the mirror coating reflectance
       curves.
   * - ``lazuli/esc/configs/*.toml``
     - The ESC optical train per arm, source and spectrum defaults, and an
       EXOSIMS parameter file.
   * - ``lazuli/esc/support_data/``
     - ESC coatings, the ZWO detector tables (gain, read noise, well depth,
       dark current, quantum efficiency), the polarizer transmission and the
       vortex off-axis throughput curve.
   * - ``lazuli/SNAPSHOT.txt``
     - Which UASAL package and revision each directory was copied from, and
       when.
   * - ``esc_filters_eol/``, ``esc_filters_bol/``
     - The twelve filter curves above, at end of life and at beginning of life.
   * - ``lazuli.mplstyle``
     - The matplotlib style the plot methods apply.

Maintainers refresh the snapshot from the installed UASAL packages with
``pip install -r scripts/requirements-uasal.txt`` followed by
``python scripts/sync_uasal_configs.py``, then commit ``esc_etc/data/lazuli/``.
The mapping from the bundled names to the upstream packages is
``esc_etc.uasal_config.UPSTREAM``, and ``tests/test_uasal_snapshot.py`` fails
when the installed packages and the snapshot drift apart.
