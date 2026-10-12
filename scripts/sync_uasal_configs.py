"""Refresh the vendored UASAL config snapshot under src/esc_etc/data/uasal/.

esc_etc ships a copy of the config_um (UM 3 m telescope) and config_um_esc (ESC
instrument) TOML files and support data so the package installs from PyPI
without the UASAL git repositories. Run this after updating those packages:

    pip install -r scripts/requirements-uasal.txt
    python scripts/sync_uasal_configs.py

Layout is identical to the source packages (configs/*.toml + support_data/...)
so the relative paths inside the TOML files resolve unchanged. Files the ETC
never opens (Zemax designs, the SN template) are skipped to keep the wheel small.
"""
import datetime
import importlib
import shutil
from pathlib import Path

PACKAGES = ["config_um", "config_um_esc"]
SKIP = {"optical_designs", "hsiao07.dat"}  # ponytail: name-based skip list; extend if UA adds more bulk files
DEST = Path(__file__).resolve().parents[1] / "src" / "esc_etc" / "data" / "uasal"


def sync(dest=DEST):
    dest.mkdir(parents=True, exist_ok=True)
    lines = [f"# Vendored UASAL config snapshot, written by scripts/sync_uasal_configs.py "
             f"on {datetime.date.today().isoformat()}"]
    for name in PACKAGES:
        mod = importlib.import_module(name)
        src = Path(mod.__file__).parent
        out = dest / name
        shutil.rmtree(out, ignore_errors=True)
        shutil.copytree(src / "configs", out / "configs")
        shutil.copytree(src / "support_data", out / "support_data",
                        ignore=lambda d, names: [n for n in names if n in SKIP or n == "__pycache__"])
        lines.append(f"{name} {mod.__version__}")
    (dest / "SNAPSHOT.txt").write_text("\n".join(lines) + "\n")
    return lines


if __name__ == "__main__":
    print("\n".join(sync()))
