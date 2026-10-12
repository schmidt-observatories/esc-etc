"""The vendored Lazuli config snapshot must load on its own and, when the
upstream UASAL packages are installed, be byte-identical to them (run
scripts/sync_uasal_configs.py if this drifts)."""

import filecmp
from pathlib import Path

import astropy.units as u
import pytest

from esc_etc import uasal_config
from esc_etc.simulation import Simulation


def test_vendored_configs_load():
    tel = uasal_config.load_config_values(uasal_config.TELESCOPE)
    esc = uasal_config.load_config_values(uasal_config.INSTRUMENT)
    assert tel["telescope"]["optics"]["m1"]["aper_clear_OD"] == "3.065m"
    assert "arm_a" in esc["common_params"]
    assert Path(uasal_config.get_data_path(uasal_config.INSTRUMENT)).is_dir()


def test_default_simulation_needs_no_uasal_packages():
    assert Simulation.from_default().get_snr(3600 * u.s, 60 * u.s)["snr"] > 0


@pytest.mark.parametrize("local, upstream", list(uasal_config.UPSTREAM.items()))
def test_snapshot_matches_installed_package(local, upstream):
    mod = pytest.importorskip(upstream)
    src = Path(mod.__file__).parent
    dst = Path(uasal_config._ROOT) / local
    stale = []
    for f in dst.rglob("*"):
        if f.is_file() and not filecmp.cmp(f, src / f.relative_to(dst), shallow=False):
            stale.append(str(f.relative_to(dst)))
    assert not stale, (
        f"vendored {local} differs from installed {upstream}; rerun scripts/sync_uasal_configs.py: {stale}"
    )
