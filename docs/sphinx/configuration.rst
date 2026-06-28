Configuration
=============

Instrument and telescope properties — mirrors, optics, coating throughputs,
filters, and detectors — are not hard-coded in ``esc_etc``. They live in the
UASAL configuration repositories and are loaded on demand by the ``from_default``
and ``from_config`` constructors.

The configuration packages
---------------------------

.. list-table::
   :header-rows: 1
   :widths: 26 74

   * - Package
     - Contents
   * - `config_um <https://github.com/uasal/config_um>`_
     - The UA Ultramarine 3 m telescope concept — primary diameter, surface /
       collecting area, focal geometry, and the detector calibration curves.
   * - `config_stp_esc <https://github.com/uasal/config_stp_esc>`_
     - The ESC instrument — optical throughputs, the focal-plane-mask (FPM)
       off-axis throughput curve, and filter definitions.
   * - `config_stp <https://github.com/uasal/config_stp>`_
     - The legacy Space Telescope Project 6.5 m concept — optional (``[dev]``
       extra); not used by the default ``arm_a`` path.
   * - `utils_config <https://github.com/uasal/utils_config>`_
     - The shared framework all of the above build on. Installed automatically.

These are declared as dependencies in ``pyproject.toml`` and installed with the
package. They are imported lazily — only when you actually call a ``from_default``
or ``from_config`` constructor — so importing ``esc_etc`` (and building these
docs) does not require them.

The default instrument
----------------------

:meth:`Simulation.from_default <esc_etc.Simulation.from_default>` assembles the
telescope, sensor, scene, and coronagraph from ``config_um`` + ``config_stp_esc``
for a given optical **arm** (default ``"arm_a"``):

.. code-block:: python

   from esc_etc import Simulation

   sim = Simulation.from_default(arm="arm_a")

Each component also has its own default constructor, all keyed on the same
``arm``:

.. code-block:: python

   from esc_etc import Telescope, Sensor, Coronagraph, get_scene

   telescope   = Telescope.from_default(arm="arm_a")
   sensor      = Sensor.from_default(telescope, arm="arm_a")
   scene       = get_scene(telescope, hoststarmag=-0.353, planetdeltamag=20.0)
   coronagraph = Coronagraph.from_default(telescope, raw_dh_contrast=1e-8,
                                          ppgain=10, separation=0.4)

Supplying your own configuration
--------------------------------

The lower-level ``from_config`` constructors accept an already-loaded config
dictionary and a support-data path, so you can point the ETC at a custom
instrument as long as it follows the same organizational structure as the UASAL
config repositories:

.. code-block:: python

   import config_stp_esc

   coronagraph = Coronagraph.from_config(
       instrument_config=config_stp_esc.load_config_values(),
       instrument_support_path=config_stp_esc.get_data_path(),
       telescope=telescope,
       raw_dh_contrast=1e-8, ppgain=10, separation=0.4, arm="arm_a",
   )

See :meth:`Sensor.from_config <esc_etc.Sensor.from_config>`,
:meth:`Telescope.from_config <esc_etc.Telescope.from_config>`, and
:meth:`Coronagraph.from_config <esc_etc.Coronagraph.from_config>` for the exact
signatures.

Overriding parameters at runtime
--------------------------------

You do not need to edit configuration files to explore parameter changes. Every
component exposes its tunable parameters through :meth:`~esc_etc.Simulation.update`
with ``child__key`` syntax, and :meth:`~esc_etc.Simulation.reset` reverts them:

.. code-block:: python

   sim.update(coronagraph__separation=0.6)
   sim.update(coronagraph__raw_dh_contrast=5e-9)
   sim.update(coronagraph__ppgain=20)
   sim.reset()

Call :meth:`~esc_etc.Simulation.describe` (inherited from the mutable-parameter
base class) on any component to print its current tunable parameters.
