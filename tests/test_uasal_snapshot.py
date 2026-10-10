"""The vendored UASAL config snapshot must load on its own and, when the
upstream packages are installed, be byte-identical to them (run
scripts/sync_uasal_configs.py if this drifts)."""
import filecmp
from pathlib import Path

import astropy.units as u
import pytest

from esc_etc import uasal_config
from esc_etc.simulation import Simulation


def test_vendored_configs_load():
    um = uasal_config.load_config_values("config_um")
    esc = uasal_config.load_config_values("config_um_esc")
    assert um["telescope"]["optics"]["m1"]["aper_clear_OD"] == "3.065m"
    assert "arm_a" in esc["common_params"]
    assert Path(uasal_config.get_data_path("config_um_esc")).is_dir()


def test_default_simulation_needs_no_uasal_packages():
    assert Simulation.from_default().get_snr(3600 * u.s, 60 * u.s)["snr"] > 0


@pytest.mark.parametrize("name", ["config_um", "config_um_esc"])
def test_snapshot_matches_installed_package(name):
    mod = pytest.importorskip(name)
    src = Path(mod.__file__).parent
    dst = Path(uasal_config._ROOT) / name
    stale = []
    for f in dst.rglob("*"):
        if f.is_file() and not filecmp.cmp(f, src / f.relative_to(dst), shallow=False):
            stale.append(str(f.relative_to(dst)))
    assert not stale, f"vendored {name} differs from installed; rerun scripts/sync_uasal_configs.py: {stale}"
