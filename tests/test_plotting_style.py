# tests/test_plotting_style.py
import pytest
import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt

from esc_etc.plotting import (
    TEAL,
    RED,
    AMBER,
    BLUE,
    GREEN,
    DARKBLUE,
    LAZULI_COLORS,
    lazuli_style,
    use_lazuli_style,
    _style_path,
    _apply_axis_cosmetics,
)


def test_color_tokens_match_canonical_hex():
    assert TEAL == "#00798c"
    assert RED == "#d1495b"
    assert AMBER == "#edae49"
    assert BLUE == "#30638e"
    assert GREEN == "#66a182"
    assert DARKBLUE == "#003d5b"
    assert LAZULI_COLORS == [TEAL, RED, AMBER, BLUE, GREEN, DARKBLUE]


def test_style_file_is_shipped_and_resolvable():
    path = _style_path()
    assert str(path).endswith("data/lazuli.mplstyle")
    text = path.read_text()
    assert "axes.prop_cycle" in text
    assert "00798c" in text


def test_lazuli_style_context_does_not_mutate_global_rcparams():
    before = plt.rcParams["xtick.direction"]
    with lazuli_style():
        assert plt.rcParams["xtick.direction"] == "in"
    assert plt.rcParams["xtick.direction"] == before


def test_use_lazuli_style_mutates_global_rcparams():
    with plt.rc_context():  # isolates the global mutation to this block
        use_lazuli_style()
        assert plt.rcParams["xtick.direction"] == "in"


def test_apply_axis_cosmetics_sets_grid_and_inward_ticks():
    fig, ax = plt.subplots()
    _apply_axis_cosmetics(ax)
    assert ax.xaxis.get_gridlines()  # grid lines exist
    plt.close(fig)


def test_lazuli_style_keeps_interactive_state_switched_on_inside_the_context():
    # Jupyter's inline backend activates lazily on the first figure, i.e. inside
    # the style context; the context must not undo that or later figures vanish.
    import matplotlib

    before = matplotlib.is_interactive()
    try:
        matplotlib.interactive(False)
        with lazuli_style():
            matplotlib.interactive(True)
        assert matplotlib.is_interactive()
    finally:
        matplotlib.interactive(before)


def test_lazuli_style_keeps_interactive_state_when_the_body_raises():
    import matplotlib

    before = matplotlib.is_interactive()
    try:
        matplotlib.interactive(False)
        with pytest.raises(RuntimeError):
            with lazuli_style():
                matplotlib.interactive(True)  # the inline backend activating
                raise RuntimeError("plot failed")
        assert matplotlib.is_interactive()
    finally:
        matplotlib.interactive(before)
