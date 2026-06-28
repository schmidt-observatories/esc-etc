import pytest
from esc_etc.meta import _MetaHolder_


class Widget(_MetaHolder_):
    def __init__(self, a, b):
        self._mutable_parameters = ["a", "b"]
        self._init_meta(a=a, b=b)


class Box(_MetaHolder_):
    def __init__(self, w):
        self._mutable_parameters = ["label"]
        self.widget = w
        self._init_meta(label="box")


def test_update_sets_mutable_attribute():
    w = Widget(1, 2)
    updated = w.update(a=10)
    assert w.a == 10
    assert updated == ["a"]


def test_update_rejects_unknown_key():
    w = Widget(1, 2)
    with pytest.raises(KeyError):
        w.update(c=5)


def test_reset_restores_initial():
    w = Widget(1, 2)
    w.update(a=10, b=20)
    w.reset()
    assert (w.a, w.b) == (1, 2)


def test_nested_update_routes_to_child():
    b = Box(Widget(1, 2))
    b.update(widget__a=99)
    assert b.widget.a == 99
