"""Refresh the vendored Lazuli config snapshot under src/esc_etc/data/lazuli/.

esc_etc ships a copy of the UASAL config_um (Lazuli 3 m telescope; "um" is
UA's code name for Lazuli) and config_um_esc (ESC instrument) TOML files and
support data, so the package installs from PyPI without the UASAL git
repositories. The copies live under the names in esc_etc.uasal_config
(``telescope`` and ``esc``); the upstream package names are only in
``uasal_config.UPSTREAM``. To pull a newer upstream version:

    pip install -r scripts/requirements-uasal.txt   # installs the UASAL packages from git
    python scripts/sync_uasal_configs.py             # copies them into the snapshot
    python -m pytest tests/test_uasal_snapshot.py    # loads the snapshot, checks it matches
    git add src/esc_etc/data/lazuli && git commit

Layout is identical to the source packages (configs/*.toml + support_data/...)
so the relative paths inside the TOML files resolve unchanged. Files the ETC
never opens (Zemax designs, the SN template) are skipped to keep the wheel small.
"""
import datetime
import importlib
import shutil
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))
from esc_etc.uasal_config import UPSTREAM, _ROOT as DEST  # noqa: E402

SKIP = {"optical_designs", "hsiao07.dat"}  # ponytail: name-based skip list; extend if UA adds more bulk files


def sync(dest=DEST):
    dest.mkdir(parents=True, exist_ok=True)
    lines = [f"# Vendored UASAL config snapshot, written by scripts/sync_uasal_configs.py "
             f"on {datetime.date.today().isoformat()}"]
    for local, upstream in UPSTREAM.items():
        mod = importlib.import_module(upstream)
        src = Path(mod.__file__).parent
        out = dest / local
        shutil.rmtree(out, ignore_errors=True)
        shutil.copytree(src / "configs", out / "configs")
        shutil.copytree(src / "support_data", out / "support_data",
                        ignore=lambda d, names: [n for n in names if n in SKIP or n == "__pycache__"])
        lines.append(f"{local} <- {upstream} {mod.__version__}")
    (dest / "SNAPSHOT.txt").write_text("\n".join(lines) + "\n")
    return lines


if __name__ == "__main__":
    print("\n".join(sync()))
