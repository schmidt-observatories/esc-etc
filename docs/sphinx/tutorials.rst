Tutorials
=========

These tutorials are runnable Jupyter notebooks from the ``notebooks/``
directory of the repository, rendered here with their saved outputs. Each one
is self-contained — download it and run it interactively to experiment. They
require the ``config_um`` / ``config_stp_esc`` configs and an editable install
(see :doc:`installation`).

.. list-table::
   :header-rows: 1
   :widths: 35 65

   * - Notebook
     - What it covers
   * - :doc:`notebooks/01_getting_started`
     - Build a :class:`~esc_etc.Simulation` with ``from_default``, compute SNR,
       and plot the noise breakdown.
   * - :doc:`notebooks/02_components_and_parameters`
     - Build :class:`~esc_etc.Telescope` / :class:`~esc_etc.Sensor` /
       :class:`~esc_etc.Scene` / :class:`~esc_etc.Coronagraph` individually,
       assemble with ``from_components``, and vary parameters via ``update()`` /
       ``reset()``.
   * - :doc:`notebooks/03_coronagraph_and_contrast`
     - The coronagraph knobs (``raw_dh_contrast``, ``ppgain``, ``separation``)
       and the off-axis throughput curve.
   * - :doc:`notebooks/04_integration_time_snr_saturation`
     - Invert SNR for an integration time, the SNR-vs-time curve, and
       saturation checks.

.. note::

   The older ``ESC_ExposureTimeSNRCalculator_Demo.ipynb`` and the various
   dated exploratory notebooks in ``notebooks/`` use the legacy API and are not
   rendered here; prefer the numbered suite above.

.. toctree::
   :maxdepth: 1
   :hidden:

   notebooks/01_getting_started
   notebooks/02_components_and_parameters
   notebooks/03_coronagraph_and_contrast
   notebooks/04_integration_time_snr_saturation
