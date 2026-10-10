import importlib.metadata
from pathlib import Path

__version__ = importlib.metadata.version(__package__)


def get_data_path():
    """Path to the packaged data directory (filter curves, vendored UASAL configs)."""
    return str(Path(__file__).parent.resolve() / "data") + "/"


from .telescope import Telescope
from .sensor import Sensor, FILTERS
from .scene import Scene, SceneElement, get_scene
from .coronagraph import Coronagraph
from .noise import AnalyticCoronagraphNoiseModel, CountRates
from .simulation import Simulation
from .ExposureTimeSNRCalculatorESC import Observatory, esc_calc_snr
from .plotting import (
    plot_count_rates, plot_snr_vs_time, plot_offaxis_throughput,
    plot_bandpass, plot_spectra, lazuli_style, use_lazuli_style,
    LAZULI_COLORS, TEAL, RED, AMBER, BLUE, GREEN, DARKBLUE,
)

__all__ = [
    "get_data_path", "__version__",
    "Simulation", "Telescope", "Sensor", "FILTERS", "Scene", "SceneElement", "Coronagraph",
    "get_scene", "AnalyticCoronagraphNoiseModel", "CountRates",
    "Observatory", "esc_calc_snr",
    "plot_count_rates", "plot_snr_vs_time", "plot_offaxis_throughput",
    "plot_bandpass", "plot_spectra", "lazuli_style", "use_lazuli_style",
    "LAZULI_COLORS", "TEAL", "RED", "AMBER", "BLUE", "GREEN", "DARKBLUE",
]
