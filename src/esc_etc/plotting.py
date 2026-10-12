# src/esc_etc/plotting.py
"""Lazuli-styled matplotlib plotting helpers for the ESC ETC.

Mirrors wcc-etc's plotting.py conventions: each helper takes the domain object
(Simulation/Coronagraph/Sensor/Scene) positionally OR explicit raw arrays as
keywords, accepts ax=None, applies the lazuli style via a context manager, and
returns (fig, ax). The style ships as data/lazuli.mplstyle (byte-identical to the
canonical lazuli-transit copy).
"""

import contextlib
import importlib.resources

import numpy as np
import matplotlib
import matplotlib.pyplot as plt
from matplotlib.colors import LogNorm
from matplotlib.patches import Circle, Rectangle
import astropy.units as u
from scipy.special import j1

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


@contextlib.contextmanager
def lazuli_style():
    """Context manager applying the lazuli style without touching global rcParams,
    except that interactive mode switched on inside the block (Jupyter's inline
    backend does this on the first figure) stays on.

    Usage: ``with lazuli_style(): ...``. Every helper wraps its drawing in this.
    """
    # Jupyter's inline backend switches interactive mode on when the first
    # figure is created, i.e. inside this block; style.context would restore
    # the old value on exit and every later figure would go undisplayed. Keep
    # the flag as it stood at the end of the block, even if the block raised.
    interactive = matplotlib.is_interactive()
    try:
        with plt.style.context(str(_style_path())):
            try:
                yield
            finally:
                interactive = matplotlib.is_interactive()
    finally:
        matplotlib.interactive(interactive)


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

    dark_total = sensor.dark_current * sensor.num_psf_pixels
    labels = ["Source", "Zodi", "Exozodi", "Speckle", "Dark"]
    values = np.array(
        [
            rates.source.value,
            rates.zodi.value,
            rates.exozodi.value,
            rates.speckle.value,
            dark_total.value,
        ],
        dtype=float,
    )
    if log:
        values = np.clip(values, 1e-30, None)

    with lazuli_style():
        fig, ax = _prepare_ax(ax)
        ax.bar(labels, values, color=LAZULI_COLORS[: len(labels)])
        if log:
            ax.set_yscale("log")
        ax.set_ylabel(r"Count rate [e$^-$/s]")
        ax.set_xlabel("Component")
        _apply_axis_cosmetics(ax)
        ax.grid(False, axis="x")  # bar chart: keep horizontal (y) grid only
    return fig, ax


def _snr_curve(sim, total_times, frame_time):
    """SNR at each of ``total_times`` with the count rates evaluated once.
    Intentionally bypasses sim.get_snr, which recomputes the rates per call."""
    rates = sim.count_rate_components()
    return np.array(
        [
            sim.noise_model.snr(rates, sim.sensor, sim.coronagraph, t, frame_time)[
                "snr"
            ]
            for t in total_times
        ],
        dtype=float,
    )


def _owner_and_attr(sim, key):
    """(component, attribute) for an ``update``-style key such as ``"coronagraph__ppgain"``."""
    *path, attr = key.split("__")
    owner = sim
    for part in path:
        owner = getattr(owner, part)
    return owner, attr


def _fmt(value):
    try:
        return format(value, "g")
    except (TypeError, ValueError):  # strings and other non-numbers
        return str(value)


def plot_snr_vs_time(
    sim=None,
    *,
    total_times=None,
    frame_time=None,
    snrs=None,
    sweep=None,
    label=None,
    ax=None,
):
    """SNR vs total integration time (log-log).

    Pass a Simulation (sweeps `total_times`, default logspace from one frame to
    1e5 s, computing SNR per point via the engine's noise_model with a single
    count-rate evaluation), or explicit `(total_times, snrs)`. `frame_time`
    defaults to 100 s.

    ``sweep={"coronagraph__raw_dh_contrast": [1e-7, 1e-8, 1e-9]}`` draws one
    curve per value of one ``update``-style parameter (any nesting, e.g.
    ``"scene__zodi__mag"``) and puts the original value back afterwards.
    ``label`` names the single curve (for a legend when drawing several onto
    one ``ax``). Returns (fig, ax).
    """
    if frame_time is None:
        frame_time = 100 * u.s
    if total_times is None and sim is not None:
        t0 = np.log10(u.Quantity(frame_time, u.s).value)
        total_times = np.logspace(t0, max(5, t0 + 1), 40) * u.s
    if sweep is not None:
        _require(sim, "sim", "sweep")
        ((key, values),) = sweep.items()
        owner, attr = _owner_and_attr(sim, key)
        previous = owner.meta[
            attr
        ]  # what was set, not a derived value (None = automatic)
        curves = []
        try:
            for v in values:
                sim.update(**{key: v})
                curves.append(
                    (f"{attr} = {_fmt(v)}", _snr_curve(sim, total_times, frame_time))
                )
        finally:
            sim.update(**{key: previous})
    else:
        if snrs is None:
            _require(sim, "snrs", "total_times")
            snrs = _snr_curve(sim, total_times, frame_time)
        curves = [(label, np.asarray(snrs, dtype=float))]

    t_s = u.Quantity(total_times, u.s).value
    with lazuli_style():
        fig, ax = _prepare_ax(ax)
        for i, (lab, y) in enumerate(curves):
            ax.loglog(
                t_s,
                y,
                color=None if label else LAZULI_COLORS[i % len(LAZULI_COLORS)],
                label=lab,
            )
        if sweep is not None or label is not None:
            ax.legend()
        ax.set_xlabel("Integration time [s]")
        ax.set_ylabel("SNR")
        _apply_axis_cosmetics(ax)
    return fig, ax


def plot_offaxis_throughput(
    coronagraph=None,
    *,
    separations=None,
    throughputs=None,
    label=None,
    ax=None,
    mark_separation=True,
):
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
        throughputs = np.array(
            [coronagraph.off_axis_throughput(float(s)) for s in separations],
            dtype=float,
        )

    with lazuli_style():
        fig, ax = _prepare_ax(ax)
        ax.plot(
            np.asarray(separations, dtype=float),
            np.asarray(throughputs, dtype=float),
            color=None if label else TEAL,
            label=label,
        )
        if mark_separation and coronagraph is not None:
            ax.axvline(
                coronagraph.separation,
                color=RED,
                ls="--",
                lw=1.0,
                label=f"separation = {coronagraph.separation} arcsec",
            )
            ax.legend()
        ax.set_xlabel("Separation [arcsec]")
        ax.set_ylabel("Off-axis throughput")
        _apply_axis_cosmetics(ax)
    return fig, ax


def plot_bandpass(
    sensor=None, *, wavelength=None, throughput=None, label=None, ax=None
):
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
        wavelength = (
            u.Quantity(wavelength).to(u.nm).value
            if hasattr(wavelength, "unit")
            else np.asarray(wavelength, dtype=float)
        )

    with lazuli_style():
        fig, ax = _prepare_ax(ax)
        ax.plot(
            np.asarray(wavelength, dtype=float),
            np.asarray(throughput, dtype=float),
            color=None if label else TEAL,
            label=label,
        )
        if label is not None:
            ax.legend()
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


def _pixelated_airy(pix_per_lamD, half_pix, sub=10):
    """Airy PSF integrated onto a (2*half_pix+1)^2 pixel grid centred on a pixel.
    Returns the fraction of the total flux in each pixel."""
    n = 2 * half_pix + 1
    d = 1.0 / sub  # pixel units
    x = np.arange(n * sub) * d - n / 2 + d / 2
    X, Y = np.meshgrid(x, x)
    R = np.hypot(X, Y) / pix_per_lamD  # lambda/D
    with np.errstate(invalid="ignore", divide="ignore"):
        I = np.where(R == 0, 1.0, (2 * j1(np.pi * R) / (np.pi * R)) ** 2)
    I *= (np.pi / 4) * (d / pix_per_lamD) ** 2
    return I.reshape(n, sub, n, sub).sum(axis=(1, 3))


def plot_aperture(sensor=None, *, ax=None, half_lamD=2.5):
    """The noise/extraction aperture drawn over a pixel-integrated Airy PSF.

    Pass a Sensor or a Simulation (uses .sensor). Shows the footprint that the
    SNR terms use: a disk for "resel"/"optimal", the n x n square for "box", and
    for "matched" a dashed circle of the equivalent area N_eff (there is no hard
    edge; every pixel is weighted). Axes are in detector pixels. Returns (fig, ax).
    """
    if sensor is not None and hasattr(sensor, "sensor"):
        sensor = sensor.sensor
    _require(sensor, "sensor", "nothing else")
    ppl = sensor.pix_per_lamD
    npix = float(sensor.num_psf_pixels.value)
    ap = sensor.aperture
    half_pix = int(np.ceil(half_lamD * ppl))
    img = _pixelated_airy(ppl, half_pix)
    ext = (-half_pix - 0.5, half_pix + 0.5, -half_pix - 0.5, half_pix + 0.5)

    with lazuli_style():
        fig, ax = _prepare_ax(ax)
        im = ax.imshow(
            img,
            extent=ext,
            origin="lower",
            cmap="Greys",
            norm=LogNorm(vmin=img.max() * 1e-4, vmax=img.max()),
        )
        for k in np.arange(-half_pix - 0.5, half_pix + 1):  # pixel grid
            ax.axhline(k, color="w", lw=0.3, alpha=0.5)
            ax.axvline(k, color="w", lw=0.3, alpha=0.5)
        if ap == "box":
            n = int(round(np.sqrt(npix)))
            ax.add_patch(Rectangle((-n / 2, -n / 2), n, n, fill=False, ec=RED, lw=2))
        else:
            r = np.sqrt(npix / np.pi)
            ax.add_patch(
                Circle(
                    (0, 0),
                    r,
                    fill=False,
                    ec=RED,
                    lw=2,
                    ls="--" if ap == "matched" else "-",
                )
            )
        ax.add_patch(Circle((0, 0), 1.22 * ppl, fill=False, ec=TEAL, lw=1, ls=":"))
        ax.set_xlim(ext[0], ext[1])
        ax.set_ylim(ext[2], ext[3])
        ax.set_aspect("equal")
        ax.set_xlabel("pixels")
        ax.set_ylabel("pixels")
        ax.set_title(
            f"aperture = {ap!r}: {npix:.1f} px, EE = {sensor.ee_fraction:.2f}\n"
            f"{ppl:.2f} px per $\\lambda/D$ at {sensor._telescope.primary_filter.to(u.nm):.0f}"
            f"  (dotted: first Airy dark ring)",
            fontsize=10,
        )
        ax.grid(False)
        ax.minorticks_off()
        fig.colorbar(
            im, ax=ax, fraction=0.046, pad=0.02, label="fraction of PSF flux per pixel"
        )
    return fig, ax


def plot_overview(sim=None, *, frame_time=None, axes=None):
    """2 x 3 overview of a Simulation: count rates, SNR vs time, bandpass;
    off-axis throughput, aperture footprint, scene spectra.

    ``axes`` may be an existing 2 x 3 array of axes. Returns (fig, axes).
    """
    _require(sim, "sim", "nothing else")
    if axes is None:
        with lazuli_style():
            fig, axes = plt.subplots(2, 3, figsize=(14, 8), layout="constrained")
    else:
        fig = np.asarray(axes).flat[0].figure
    a = np.asarray(axes)
    plot_count_rates(sim, ax=a[0, 0])
    plot_snr_vs_time(sim, frame_time=frame_time, ax=a[0, 1])
    plot_bandpass(sim, ax=a[0, 2])
    plot_offaxis_throughput(sim, ax=a[1, 0])
    plot_aperture(sim, ax=a[1, 1])
    plot_spectra(sim, ax=a[1, 2])
    return fig, axes
