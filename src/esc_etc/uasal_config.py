"""Vendored UASAL configs (config_um, config_um_esc) shipped inside esc_etc.

Mirrors the two functions the ETC used from those packages so the defaults
work from a plain PyPI install. Refresh the snapshot with
scripts/sync_uasal_configs.py; provenance is in data/uasal/SNAPSHOT.txt.
"""
import tomllib
from pathlib import Path

_ROOT = Path(__file__).parent / "data" / "uasal"


def load_config_values(package):
    """Raw TOML dicts keyed by file stem, as ``<package>.load_config_values()`` returns."""
    cfg = {}
    for f in sorted((_ROOT / package / "configs").glob("*.toml")):
        with open(f, "rb") as fh:
            cfg[f.stem] = tomllib.load(fh)
    return cfg


def get_data_path(package):
    """``<package>/support_data/`` with a trailing slash, as ``<package>.get_data_path()`` returns."""
    p = _ROOT / package / "support_data"
    if not p.exists():
        raise FileNotFoundError(f"Vendored UASAL support data not found: {p}")
    return str(p) + "/"
