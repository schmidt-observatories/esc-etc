Configuration
=============

Instrument and telescope properties (mirrors, optics, coating throughputs,
filters, detector tables) are not hard-coded in ``esc_etc``. They come from the
UASAL configuration packages `config_um <https://github.com/uasal/config_um>`_
(the UA Ultramarine 3 m telescope) and `config_um_esc
<https://github.com/uasal/config_um_esc>`_ (the ESC instrument).

A snapshot of those files ships inside the package
--------------------------------------------------

``esc_etc`` does not depend on the config packages at install time. A copy of
their ``configs/`` and ``support_data/`` trees is vendored under
``esc_etc/data/uasal/`` and read by the small ``esc_etc.uasal_config`` module,
so a plain ``pip install`` needs no git access. ``SNAPSHOT.txt`` next to the
files records which revision of each package the snapshot came from.

Maintainers refresh the snapshot from the installed packages with:

.. code-block:: bash

   pip install -r scripts/requirements-uasal.txt   # the git packages
   python scripts/sync_uasal_configs.py

``tests/test_uasal_snapshot.py`` fails when the installed packages and the
snapshot drift apart.

The default instrument
----------------------

:meth:`Simulation.from_default <esc_etc.Simulation.from_default>` assembles the
telescope, sensor, scene and coronagraph from the snapshot for a given optical
**arm** (default ``"arm_a"``):

.. code-block:: python

   from esc_etc import Simulation

   sim = Simulation.from_default(arm="arm_a")
   sim = Simulation.from_default(filter="F630N", lifetime="eol")

``filter`` (a key of :data:`esc_etc.FILTERS`, by wheel slot such as ``"R2"`` or
designation such as ``"F630N"``) replaces the generic configuration bandpass
with that filter's measured end-to-end curve and moves the telescope's design
wavelength to match. ``lifetime`` selects the ``"eol"`` (end of life, the
default) or ``"bol"`` (beginning of life) curve set; it needs a named filter,
and any other value raises ``ValueError``. Without ``filter`` you get the
generic chain built from the configuration files, which is wider and a little
more transmissive than any real filter.

Each component also has its own default constructor, keyed on the same ``arm``
and ``filter``. The telescope and the sensor must be built for the same filter;
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
instrument that follows the same layout as the UASAL packages. The vendored
snapshot is loaded the same way:

.. code-block:: python

   from esc_etc import uasal_config

   coronagraph = Coronagraph.from_config(
       instrument_config=uasal_config.load_config_values("config_um_esc"),
       instrument_support_path=uasal_config.get_data_path("config_um_esc"),
       telescope=telescope,
       raw_dh_contrast=1e-8, ppgain=10, separation=0.4, arm="arm_a",
   )

See :meth:`Sensor.from_config <esc_etc.Sensor.from_config>`,
:meth:`Telescope.from_config <esc_etc.Telescope.from_config>` and
:meth:`Coronagraph.from_config <esc_etc.Coronagraph.from_config>` for the exact
signatures.

Overriding parameters at runtime
--------------------------------

You do not need to edit configuration files to explore parameter changes. Every
component exposes its tunable parameters through
:meth:`~esc_etc.Simulation.update` with ``child__key`` syntax, and
:meth:`~esc_etc.Simulation.reset` reverts the whole simulation:

.. code-block:: python

   sim.update(coronagraph__separation=0.6)
   sim.update(coronagraph__raw_dh_contrast=5e-9, coronagraph__ppgain=20)
   sim.update(sensor__aperture="optimal")
   sim.reset()

Call ``describe()`` on a component (``sim.sensor.describe()``) to print its
tunable parameters. The simulation itself has none; everything lives on the
components.
