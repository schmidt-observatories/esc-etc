"""The Lazuli configuration shipped inside esc_etc.

The telescope and ESC instrument TOML files and their support data are a
snapshot of two University of Arizona Space Astrophysics Lab (UASAL) packages,
copied under ``data/lazuli/`` so the package installs from PyPI without git
access. Code refers to them as :data:`TELESCOPE` and :data:`INSTRUMENT`; the
upstream package names appear only in :data:`UPSTREAM`, which
``scripts/sync_uasal_configs.py`` and the drift test use. Provenance is in
``data/lazuli/SNAPSHOT.txt``.
"""

import tomllib
from pathlib import Path

_ROOT = Path(__file__).parent / "data" / "lazuli"

TELESCOPE = "telescope"
"""Name of the vendored telescope configuration (the Lazuli 3 m)."""

INSTRUMENT = "esc"
"""Name of the vendored instrument configuration (the ESC)."""

UPSTREAM = {TELESCOPE: "config_um", INSTRUMENT: "config_um_esc"}
"""Vendored name -> UASAL package it is copied from ("um" is UA's code name for Lazuli)."""


def load_config_values(name):
    """Raw TOML dicts keyed by file stem, as the upstream ``load_config_values()`` returns."""
    cfg = {}
    for f in sorted((_ROOT / name / "configs").glob("*.toml")):
        with open(f, "rb") as fh:
            cfg[f.stem] = tomllib.load(fh)
    return cfg


def get_data_path(name):
    """``<name>/support_data/`` with a trailing slash, as the upstream ``get_data_path()`` returns."""
    p = _ROOT / name / "support_data"
    if not p.exists():
        raise FileNotFoundError(f"Vendored support data not found: {p}")
    return str(p) + "/"
