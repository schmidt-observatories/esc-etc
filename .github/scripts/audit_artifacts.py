"""Fail the build if dist/ artifacts carry junk, miss bundled data, or exceed the size ceiling.

The wheel's data files come from filesystem globs in pyproject.toml, so anything
dropped into src/esc_etc/data/ on a developer machine can ship. This is the check
that it did not, and that everything the package opens at run time is present.
"""

import glob
import os
import re
import sys
import tarfile
import zipfile

JUNK = re.compile(
    r"\.DS_Store$|\.sw[op]$|\.prof$|\.ipynb_checkpoints/|__pycache__/"
    r"|esc_filters_eol_old/|docs/superpowers/|notebooks/|input_scrap/"
)
REQUIRED = [
    "esc_etc/_version.py",
    "esc_etc/data/lazuli.mplstyle",
    "esc_etc/data/uasal/SNAPSHOT.txt",
    "esc_etc/data/uasal/config_um/configs/telescope.toml",
    "esc_etc/data/uasal/config_um_esc/configs/common_params.toml",
    "esc_etc/data/uasal/config_um_esc/support_data/transmissive_optics/vvc_throughput_vs_lamD.fits",
]
FILTER_SETS = {"esc_filters_eol": 12, "esc_filters_bol": 12}  # curves per lifetime
MAX_BYTES = 5 * 1024**2  # clean wheel is ~0.9 MB, sdist ~1.9 MB


def entries(path):
    if path.endswith(".whl"):
        return zipfile.ZipFile(path).namelist()
    with tarfile.open(path) as tar:
        return tar.getnames()


def problems(names, size):
    out = []
    if size > MAX_BYTES:
        out.append(f"over the {MAX_BYTES / 1024**2:.0f} MB ceiling")
    out += [f"junk in artifact: {n}" for n in names if JUNK.search(n)]
    out += [f"missing: {r}" for r in REQUIRED if not any(n.endswith(r) for n in names)]
    for folder, count in FILTER_SETS.items():
        found = sum(1 for n in names if re.search(rf"{folder}/[^/]+\.csv$", n))
        if found != count:
            out.append(f"{folder}: {found} curves, expected {count}")
    return out


def main():
    paths = sorted(glob.glob("dist/*"))
    if not paths:
        print("FAIL: dist/ is empty")
        return 1
    bad = False
    for path in paths:
        names = entries(path)
        size = os.path.getsize(path)
        print(f"{path}: {size / 1024**2:.1f} MB, {len(names)} entries")
        for p in problems(names, size):
            print(f"  FAIL: {p}")
            bad = True
    return 1 if bad else 0


if __name__ == "__main__":
    sys.exit(main())
