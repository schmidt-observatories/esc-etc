# tests/test_scene.py
import astropy.units as u
import pytest


from esc_etc.telescope import Telescope
from esc_etc.scene import Scene, SceneElement, get_scene


def test_get_scene_elements():
    t = Telescope.from_default()
    scene = get_scene(
        t, hoststarmag=-0.353, planetdeltamag=20.0, bg_flux=22.5, exobg_flux=21.0
    )
    assert isinstance(scene.star, SceneElement)
    assert scene.star.mag == pytest.approx(-0.353)
    assert scene.planet.deltamag == pytest.approx(20.0)
    assert scene.zodi.mag == pytest.approx(22.5)
    # exozodi magnitude is host + exo offset (matches make_observation)
    assert scene.exozodi.mag == pytest.approx(-0.353 + 21.0)


def test_update_routes_to_star():
    t = Telescope.from_default()
    scene = get_scene(t, hoststarmag=0.0)
    scene.update(star__mag=2.0)
    assert scene.star.mag == 2.0
