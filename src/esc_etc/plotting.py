# src/esc_etc/plotting.py
"""Lazuli-styled matplotlib plotting helpers for the ESC ETC.

Mirrors wcc-etc's plotting.py conventions: each helper takes the domain object
(Simulation/Coronagraph/Sensor/Scene) positionally OR explicit raw arrays as
keywords, accepts ax=None, applies the lazuli style via a context manager, and
returns (fig, ax). The style ships as data/lazuli.mplstyle (byte-identical to the
canonical lazuli-transit copy).
"""
import importlib.resources

import numpy as np
import matplotlib.pyplot as plt

# Lazuli qualitative palette (hex), in prop_cycle order.
TEAL = "#00798c"
RED = "#d1495b"
AMBER = "#edae49"
BLUE = "#30638e"
GREEN = "#66a182"
DARKBLUE = "#003d5b"
LAZULI_COLORS = [TEAL, RED, AMBER, BLUE, GREEN, DARKBLUE]


def _style_path():
    """Filesystem path to the shipped lazuli.mplstyle."""
    return importlib.resources.files("esc_etc") / "data" / "lazuli.mplstyle"


def lazuli_style():
    """Context manager applying the lazuli style without touching global rcParams.

    Usage: ``with lazuli_style(): ...``. Every helper wraps its drawing in this.
    """
    return plt.style.context(str(_style_path()))


def use_lazuli_style():
    """Apply the lazuli style to matplotlib's global rcParams (opt-in, mutates state)."""
    plt.style.use(str(_style_path()))


def _apply_axis_cosmetics(ax):
    """Inward minor+major ticks on all sides and a subtle grid.

    Applied to whatever axis a helper draws on so a user-supplied `ax` (whose
    rcParams were fixed at creation) still gets the lazuli look.
    """
    ax.minorticks_on()
    ax.tick_params(which="both", direction="in", top=True, right=True)
    ax.grid(True, alpha=0.3, linewidth=0.3)


def _prepare_ax(ax):
    """Return (fig, ax): create a new fig/ax if ax is None, else reuse the given ax."""
    if ax is None:
        fig, ax = plt.subplots()
    else:
        fig = ax.figure
    return fig, ax


def _require(value, name, alt):
    """Raise a clear ValueError when neither a domain object nor its arrays were given."""
    if value is None:
        raise ValueError(
            f"Provide either a domain object or {name!r} (and {alt}). Got neither."
        )
    return value
