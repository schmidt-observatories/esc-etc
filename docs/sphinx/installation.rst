Installation
============

Requirements
------------

- **Python 3.11 or newer.**
- The scientific stack pulled in automatically as dependencies: ``numpy``,
  ``astropy``, ``synphot``, ``matplotlib``, ``pandas``, and ``scipy``.
- The UASAL configuration files for ``config_um`` (UA Ultramarine 3 m telescope
  concept) and ``config_um_esc`` (the ESC instrument) ship inside the package
  under ``esc_etc/data/uasal/``, so no git packages are needed. Maintainers
  refresh that snapshot with ``scripts/sync_uasal_configs.py``. See
  :doc:`configuration`.

Install from source (recommended)
---------------------------------

The package is developed on GitHub. Clone it and install in *editable* mode so
local changes to ``src/`` are picked up immediately:

.. code-block:: bash

   git clone https://github.com/schmidt-observatories/esc-etc.git
   cd esc-etc
   pip install -e .

.. important::

   Use an **editable** install (``pip install -e .``). A plain ``pip install .``
   copies the package into ``site-packages`` and can shadow the repository's
   ``src/`` tree, reintroducing import/version surprises. For development always
   prefer ``-e``.

To additionally pull the optional development dependencies (``pytest``,
``build``, ``twine``):

.. code-block:: bash

   pip install -e '.[dev]'

Verify the installation
------------------------

.. code-block:: python

   import esc_etc
   print(esc_etc.__version__)

   from esc_etc import Simulation
   import astropy.units as u

   sim = Simulation.from_default(separation=0.4, contrast=1e-8, ppgain=10)
   print(sim.get_snr(total_time=3600 * u.s, frame_time=100 * u.s)["snr"])

If that prints a version string and a signal-to-noise value, you are ready to
go. Continue with :doc:`quickstart`.

Running the test suite
----------------------

The package ships with a ``pytest`` suite. From the repository root:

.. code-block:: bash

   pip install -e '.[dev]'    # editable install + pytest, ruff, build, twine
   pytest

The same suite runs on every pull request (``.github/workflows/tests.yml``).

Building the documentation locally
-----------------------------------

The documentation you are reading is built with `Sphinx
<https://www.sphinx-doc.org>`_ and the *Read the Docs* theme. The tutorial
pages are rendered from the Jupyter notebooks via `nbsphinx
<https://nbsphinx.readthedocs.io>`_, which requires `pandoc
<https://pandoc.org>`_ to be installed.

.. code-block:: bash

   # from the repository root
   pip install -e .                              # so autodoc can import the package
   pip install -r docs/sphinx/requirements.txt   # Sphinx + theme + nbsphinx
   # plus a pandoc binary, e.g.  conda install pandoc   or   brew install pandoc

   cd docs/sphinx
   make html

Open ``docs/sphinx/_build/html/index.html`` in a browser. To force a clean
rebuild, run ``make clean html``.
