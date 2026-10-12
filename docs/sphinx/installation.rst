Installation
============

Requirements
------------

Python 3.11 or newer. The scientific stack (``numpy``, ``scipy``, ``astropy``,
``synphot``, ``matplotlib``, ``pandas``) is installed automatically, and the
instrument configuration ships inside the package, so nothing else has to be
downloaded.

Install from source
-------------------

The package is developed on GitHub. Clone it and install it in editable mode,
so that changes to ``src/`` are picked up without reinstalling:

.. code-block:: bash

   git clone https://github.com/schmidt-observatories/esc-etc.git
   cd esc-etc
   pip install -e .

.. important::

   Use the editable install (``pip install -e .``). A plain ``pip install .``
   copies the package into ``site-packages``, where it can shadow the
   repository's ``src/`` tree and cause import and version surprises.

The optional extras:

.. code-block:: bash

   pip install -e ".[dev]"    # pytest, ruff, build, twine
   pip install -e ".[docs]"   # Sphinx, the Read the Docs theme, nbsphinx

Once the package is on PyPI, ``pip install esc_etc`` installs a release
without cloning.

Using a conda environment
-------------------------

.. code-block:: bash

   conda create -n esc-etc python=3.11
   conda activate esc-etc
   pip install -e .

Verify the installation
-----------------------

.. code-block:: python

   import esc_etc
   print(esc_etc.__version__)

   from esc_etc import Simulation

   sim = Simulation.from_default(separation=0.4, contrast=1e-8, ppgain=10)
   print(sim.get_snr(total_time=3600, frame_time=100)["snr"])   # about 9.87

The last line is the signal-to-noise for the default scene, a host star of
ESC-band magnitude -0.353 with a planet 20 magnitudes fainter at 0.4 arcsec,
integrated for one hour in 100 s frames. Continue with :doc:`quickstart`.

Running the test suite
----------------------

.. code-block:: bash

   pip install -e ".[dev]"
   pytest

Every pull request runs the same suite, ``ruff`` (undefined names, unused
imports and formatting), and a build of the sdist and wheel that is then
installed in a clean environment and smoke-tested
(``.github/workflows/tests.yml``).

Building the documentation locally
----------------------------------

The site is built with `Sphinx <https://www.sphinx-doc.org>`_ and the Read
the Docs theme. The tutorial pages are rendered from the Jupyter notebooks by
`nbsphinx <https://nbsphinx.readthedocs.io>`_, which needs a `pandoc
<https://pandoc.org>`_ binary.

.. code-block:: bash

   pip install -e ".[docs]"
   brew install pandoc         # or: conda install pandoc / apt-get install pandoc
   cd docs/sphinx
   make html

Open ``docs/sphinx/_build/html/index.html`` in a browser. ``make clean html``
forces a full rebuild. The notebooks are rendered from their saved outputs, so
the build itself executes no code.
