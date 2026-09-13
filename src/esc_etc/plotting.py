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
import astropy.units as u

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


def plot_count_rates(sim=None, *, rates=None, sensor=None, ax=None, log=True):
    """Bar chart of count-rate contributors (e-/s): source, zodi, exozodi,
    speckle, and dark-current total (dark_current * num_psf_pixels).

    Pass a Simulation, or explicit `rates` (CountRates) + `sensor`. Returns (fig, ax).
    """
    if sim is not None:
        rates = sim.count_rate_components()
        sensor = sim.sensor
    _require(rates, "rates", "sensor")
    _require(sensor, "sensor", "rates")

    dark_total = (sensor.dark_current * sensor.num_psf_pixels)
    labels = ["Source", "Zodi", "Exozodi", "Speckle", "Dark"]
    values = np.array([
        rates.source.value, rates.zodi.value, rates.exozodi.value,
        rates.speckle.value, dark_total.value,
    ], dtype=float)
    if log:
        values = np.clip(values, 1e-30, None)

    with lazuli_style():
        fig, ax = _prepare_ax(ax)
        ax.bar(labels, values, color=LAZULI_COLORS[:len(labels)])
        if log:
            ax.set_yscale("log")
        ax.set_ylabel(r"Count rate [e$^-$/s]")
        ax.set_xlabel("Component")
        _apply_axis_cosmetics(ax)
        ax.grid(False, axis="x")  # bar chart: keep horizontal (y) grid only
    return fig, ax


def plot_snr_vs_time(sim=None, *, total_times=None, frame_time=None, snrs=None, ax=None):
    """SNR vs total integration time (log-log).

    Pass a Simulation (sweeps `total_times`, default logspace from one frame to
    1e5 s, computing SNR per point via the engine's noise_model with a single
    count-rate evaluation), or explicit `(total_times, snrs)`. `frame_time`
    defaults to 100 s. Returns (fig, ax).
    """
    if frame_time is None:
        frame_time = 100 * u.s
    if total_times is None and sim is not None:
        t0 = np.log10(u.Quantity(frame_time, u.s).value)
        total_times = np.logspace(t0, max(5, t0 + 1), 40) * u.s
    if snrs is None:
        _require(sim, "snrs", "total_times")
        # Intentionally bypasses sim.get_snr (which recomputes count rates each call):
        # evaluate count rates ONCE, then vary only the time in the noise model.
        rates = sim.count_rate_components()
        snrs = np.array([
            sim.noise_model.snr(rates, sim.sensor, sim.coronagraph, t, frame_time)["snr"]
            for t in total_times
        ], dtype=float)

    t_s = u.Quantity(total_times, u.s).value
    with lazuli_style():
        fig, ax = _prepare_ax(ax)
        ax.loglog(t_s, np.asarray(snrs, dtype=float), color=TEAL)
        ax.set_xlabel("Integration time [s]")
        ax.set_ylabel("SNR")
        _apply_axis_cosmetics(ax)
    return fig, ax


def plot_offaxis_throughput(coronagraph=None, *, separations=None, throughputs=None,
                            ax=None, mark_separation=True):
    """Coronagraph off-axis (FPM) throughput vs planet separation (arcsec).

    Pass a Coronagraph, a Simulation (uses .coronagraph), or explicit
    (separations, throughputs). When `mark_separation`, draws a vertical marker at
    the coronagraph's current separation. Returns (fig, ax).
    """
    if coronagraph is not None and hasattr(coronagraph, "coronagraph"):
        coronagraph = coronagraph.coronagraph  # a Simulation was passed
    if throughputs is None:
        _require(coronagraph, "throughputs", "separations")
        if separations is None:
            separations = np.linspace(0.05, 0.6, 60)
        throughputs = np.array([coronagraph.off_axis_throughput(float(s))
                                for s in separations], dtype=float)

    with lazuli_style():
        fig, ax = _prepare_ax(ax)
        ax.plot(np.asarray(separations, dtype=float),
                np.asarray(throughputs, dtype=float), color=TEAL)
        if mark_separation and coronagraph is not None:
            ax.axvline(coronagraph.separation, color=RED, ls="--", lw=1.0,
                       label=f"separation = {coronagraph.separation} arcsec")
            ax.legend()
        ax.set_xlabel("Separation [arcsec]")
        ax.set_ylabel("Off-axis throughput")
        _apply_axis_cosmetics(ax)
    return fig, ax


def plot_bandpass(sensor=None, *, wavelength=None, throughput=None, ax=None):
    """Instrument bandpass throughput vs wavelength (nm).

    Pass a Sensor, a Simulation (uses .sensor), or explicit (wavelength, throughput).
    `wavelength` may be an astropy Quantity (converted to nm) or a plain array (nm).
    Returns (fig, ax).
    """
    if sensor is not None and hasattr(sensor, "sensor"):
        sensor = sensor.sensor  # a Simulation was passed
    if throughput is None:
        _require(sensor, "throughput", "wavelength")
        bp = sensor.bandpass
        wave_q = bp.waveset  # astropy Quantity (Angstrom)
        wavelength = wave_q.to(u.nm).value
        tput = bp(wave_q)
        throughput = np.asarray(getattr(tput, "value", tput), dtype=float)
    else:
        wavelength = (u.Quantity(wavelength).to(u.nm).value
                      if hasattr(wavelength, "unit") else np.asarray(wavelength, dtype=float))

    with lazuli_style():
        fig, ax = _prepare_ax(ax)
        ax.plot(np.asarray(wavelength, dtype=float),
                np.asarray(throughput, dtype=float), color=TEAL)
        ax.set_xlabel("Wavelength [nm]")
        ax.set_ylabel("Throughput")
        _apply_axis_cosmetics(ax)
    return fig, ax


def plot_spectra(scene=None, *, which=("star", "planet", "zodi"), ax=None):
    """Scene element spectra over 3000-9000 Angstrom.

    Pass a Scene or a Simulation (uses .scene). `which` names the elements to draw.
    Returns (fig, ax).
    """
    if scene is not None and hasattr(scene, "scene"):
        scene = scene.scene  # a Simulation was passed
    _require(scene, "scene", "which")

    wave = np.arange(3000, 9000, 5) * u.AA
    wave_nm = wave.to(u.nm).value
    with lazuli_style():
        fig, ax = _prepare_ax(ax)
        for i, name in enumerate(which):
            element = getattr(scene, name)
            flux = element.spectrum(wave)
            y = np.asarray(getattr(flux, "value", flux), dtype=float)
            ax.plot(wave_nm, y, color=LAZULI_COLORS[i % len(LAZULI_COLORS)], label=name)
        ax.set_xlabel("Wavelength [nm]")
        ax.set_ylabel("Flux [PHOTLAM]")
        ax.legend()
        _apply_axis_cosmetics(ax)
    return fig, ax
