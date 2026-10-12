Tutorials
=========

The tutorials are the Jupyter notebooks in the ``notebooks/`` directory of the
repository, shown here with their saved outputs. Each one runs on its own
with an editable install (see :doc:`installation`), so download one and
change the numbers.

.. list-table::
   :header-rows: 1
   :widths: 35 65

   * - Notebook
     - What it covers
   * - :doc:`notebooks/01_getting_started`
     - SNR for a given time, time for a target SNR, the count-rate budget and
       the ``sim.plot()`` overview.
   * - :doc:`notebooks/02_components_and_parameters`
     - The four components, the photometric aperture choice, the ESC filter
       set with end-of-life and beginning-of-life curves,
       ``from_components``, ``update()`` and ``reset()``.
   * - :doc:`notebooks/03_coronagraph_and_contrast`
     - What contrast, post-processing gain and separation do to the SNR curve,
       drawn with ``plot_snr_vs_time(sweep=...)``, plus reference subtraction.
   * - :doc:`notebooks/04_integration_time_snr_saturation`
     - Frame time and read noise, inverting for integration time, and the
       saturation check with its caveat.

The same directory also holds ``ESC_ExposureTimeSNRCalculator_Demo.ipynb``
and ``etc_esc_requirements.py``, which use the pre-refactor API and do not
run; they are kept for reference only.

.. toctree::
   :maxdepth: 1
   :hidden:

   notebooks/01_getting_started
   notebooks/02_components_and_parameters
   notebooks/03_coronagraph_and_contrast
   notebooks/04_integration_time_snr_saturation
