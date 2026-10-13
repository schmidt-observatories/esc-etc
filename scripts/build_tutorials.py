"""Builder for the four esc_etc tutorial notebooks. Rebuild with
python build_tutorials.py <repo>/notebooks ; then execute with nbconvert."""
import sys
from pathlib import Path
import nbformat as nbf
from nbformat.v4 import new_notebook, new_markdown_cell as md, new_code_cell as code

OUT = Path(sys.argv[1])
META = {"kernelspec": {"display_name": "Python 3", "language": "python", "name": "python3"},
        "language_info": {"name": "python"}}

REQ = ("> Requirements: `pip install -e .` from the repo root. The instrument configuration "
       "(UM 3 m ESC) ships inside the package, so nothing else needs to be installed.")
REQ_SHORT = "> Requirements: an editable install (`pip install -e .`), as in notebook 01."


def write(name, cells):
    nb = new_notebook(); nb["cells"] = cells; nb["metadata"] = META
    nbf.write(nb, OUT / name)
    print("wrote", name, len(cells), "cells")


# ---------------------------------------------------------------- 01
write("01_getting_started.ipynb", [
md(f"""# 01 Getting started with esc_etc

`esc_etc` is the exposure-time calculator for the ESC, the coronagraphic camera on Lazuli, a 3 m telescope. It answers two questions: what signal-to-noise ratio (SNR) a planet reaches in a given integration time, and how long it takes to reach a target SNR. This notebook goes from an empty session to both answers, then shows where the noise comes from.

{REQ}"""),
code("""import astropy.units as u
import esc_etc
from esc_etc import Simulation, use_lazuli_style

use_lazuli_style()      # house plotting style for the whole session
print('esc_etc', esc_etc.__version__)"""),
md("""## 1. A default simulation

`Simulation.from_default()` builds the four pieces of the calculator (telescope, sensor, scene, coronagraph) from the packaged configuration. The arguments below are the defaults, written out so you can see what a scene is: a host star of Vega magnitude -0.353, a planet 20 magnitudes fainter at 0.2 arcsec, a raw dark-hole contrast of 1e-8, and a post-processing gain of 10. The bandpass is the end-of-life curve of the `F630N` filter (notebook 02 shows the alternatives). Magnitudes are quoted in the ESC band unless you say otherwise (notebook 02)."""),
code("""sim = Simulation.from_default(
    hoststarmag=-0.353, planetdeltamag=20,
    contrast=1e-8, ppgain=10, separation=0.2,
)
sim"""),
md("""## 2. SNR for a given integration time

`get_snr` takes the total on-target time and the length of one detector frame. Both accept astropy quantities or plain numbers, which are read as seconds. The result is a dictionary: `snr`, the integrated planet signal and total noise in electrons, and `M`, the post-processing noise floor (more on that in notebook 03)."""),
code("""out = sim.get_snr(total_time=3600 * u.s, frame_time=100 * u.s)
print('SNR          :', round(out['snr'], 3))
print('signal [e-]  :', round(out['signal_e'], 1))
print('noise  [e-]  :', round(out['noise_e'], 1))

# plain floats are seconds; hours work too
assert sim.get_snr(3600, 100)['snr'] == out['snr']
assert sim.get_snr(1 * u.h, 100)['snr'] == out['snr']
assert abs(out['snr'] - 9.75) < 0.05, out['snr']"""),
md("""## 3. Integration time for a target SNR

`get_int_time_for_snr` is the inverse. `int_time` is rounded up to whole frames; `int_time_continuous` is the exact solution. The 3600 s above round-trips. SNR 5 is reached in about 30 s because it is only half of this scene's plateau of 10; the last factor of two toward the plateau takes most of the hour (notebook 03 explains the plateau)."""),
code("""back = sim.get_int_time_for_snr(out['snr'], frame_time=100)
five = sim.get_int_time_for_snr(5, frame_time=100)
print('time to recover the SNR above :', back['int_time'][0])
print('time to SNR 5                 :', five['int_time_continuous'][0])
assert abs(back['int_time'][0].value - 3600) < 1"""),
md("""## 4. Where the noise comes from

`count_rate_components` returns the per-second electron rates inside the photometric aperture: the planet (`source`), zodiacal and exozodiacal light, residual speckles, and the host rate after the focal-plane mask. The speckle rate is `host x contrast x EE`, where EE is the fraction of a point source that falls inside the aperture (0.456 for the default aperture, see notebook 02): 5.4e8 x 1e-8 x 0.456 = 2.48 e/s. The planet gets the same EE factor, so with a contrast of 1e-8 and a planet 20 mag fainter the two rates come out equal, which is no accident: 10^(-0.4 x 20) = 1e-8."""),
code("""rates = sim.count_rate_components()
for name in ['source', 'zodi', 'exozodi', 'speckle', 'host']:
    print(f'{name:8s}: {getattr(rates, name):.3e}')

fig, ax = sim.plot_count_rates()
ax.set_title('Count rates in the photometric aperture');"""),
md("""## 5. Everything at once

`sim.plot()` draws the six standard panels. Every panel is also its own method (`sim.plot_snr_vs_time()`, `sim.plot_bandpass()`, and so on), and each accepts `ax=` so you can place it in your own figure."""),
code("""fig, axes = sim.plot()"""),
md("""Notebook 02 takes the simulation apart into its components and shows how to change parameters."""),
])

# ---------------------------------------------------------------- 02
write("02_components_and_parameters.ipynb", [
md(f"""# 02 Components and parameters

A `Simulation` is a `Telescope`, a `Sensor`, a `Scene` and a `Coronagraph`. This notebook builds each one, looks at what it holds, assembles them by hand, and changes parameters with `update()` and `reset()`. It also covers the two choices that most affect the numbers: the photometric aperture and the filter curve.

{REQ_SHORT}"""),
code("""import numpy as np
import astropy.units as u
import matplotlib.pyplot as plt
from esc_etc import (Telescope, Sensor, get_scene, Coronagraph, Simulation,
                     FILTERS, use_lazuli_style)
use_lazuli_style()"""),
md("""## 1. Telescope

The collecting area is the Lyot-stop area, which is smaller than the 3 m primary. `resel` is the solid angle of a disk of diameter lambda/D at the design wavelength; it is the default photometric aperture."""),
code("""t = Telescope.from_default()
print('primary diameter :', t.diameter_primary)
print('collecting area  :', t.surface)
print('f-number         :', round(t.f_num, 1))
print('resel            :', t.resel)"""),
md("""## 2. Sensor: detector and bandpass

The sensor holds the detector noise properties and the full non-coronagraphic throughput curve (`bandpass`). `num_psf_pixels` is the photometric aperture in detector pixels and `ee_fraction` is the fraction of an unaberrated Airy pattern that lands inside it. Both follow from `aperture`:

| `aperture` | what it is | pixels | encircled energy |
|---|---|---|---|
| `"resel"` (default) | disk of diameter lambda/D | 19.6 | 0.46 |
| `"optimal"` | disk of radius 0.7 lambda/D | 38 | 0.68 |
| `"box"` | square of side 2.44 lambda/D | 169 | 0.85 |
| `"matched"` | PSF-weighted sum; the matched-filter limit, not what a pipeline delivers | 70 (effective) | 1.00 |

The SNR barely moves between them for this scene because it is speckle limited, so the choice matters more for faint planets where read noise and background count. You can also override `encircled_energy` directly; it must be a fraction in (0, 1]."""),
code("""s = Sensor.from_default(t)
print('gain         :', s.gain)
print('read noise   :', s.read_noise)
print('dark current :', s.dark_current)
print('well depth   :', s.well_depth)
print('aperture     :', s.aperture, '|', s.num_psf_pixels, '| EE', round(s.ee_fraction, 3))
assert np.isclose(s.num_psf_pixels.value * s.plate_scale**2, t.resel.value)

fig, ax = s.plot_aperture()"""),
md("""## 3. Filters

`FILTERS` lists the ESC filter set. Passing `filter=` to `Simulation.from_default` uses that filter's measured curve as the whole bandpass and moves the telescope's design wavelength to match; `lifetime="eol"` (the default) or `"bol"` selects the end-of-life or beginning-of-life curve. The default is `DEFAULT_FILTER` (`F630N`, end of life). `filter=None` is the legacy option: the generic configuration chain, which is wider and a little more transmissive than any real filter.

When you build the components yourself, the telescope and the sensor must be built for the same filter. Mixing them raises a `ValueError`, because the pixel geometry would be computed at one wavelength and the throughput at another."""),
code("""print(sorted(FILTERS))

fig, ax = plt.subplots()
Simulation.from_default(filter=None).plot_bandpass(ax=ax, label='generic chain (filter=None)')
Simulation.from_default(filter='F630N', lifetime='eol').plot_bandpass(ax=ax, label='F630N end of life')
Simulation.from_default(filter='F630N', lifetime='bol').plot_bandpass(ax=ax, label='F630N beginning of life')
ax.set_xlim(610, 650);

try:
    Sensor.from_default(Telescope.from_default(), filter='B1')
except ValueError as err:
    print('mismatch refused:', err)"""),
md("""## 4. Scene and coronagraph

`get_scene` builds the star, planet, zodi and exozodi elements. The star and planet magnitudes are Vega magnitudes in the ESC band by default; `hoststar_band=` and `mag_system=` change that. The coronagraph carries the raw dark-hole contrast, the post-processing gain and the planet separation."""),
code("""scene = get_scene(t, hoststarmag=-0.353, planetdeltamag=20, bg_flux=22.5, exobg_flux=21)
c = Coronagraph.from_default(t, raw_dh_contrast=1e-8, ppgain=10, separation=0.2)
print('star mag    :', scene.star.mag, scene.star.mag_system)
print('planet dmag :', scene.planet.deltamag)
print('contrast    :', c.raw_dh_contrast, '| ppgain', c.ppgain, '| separation', c.separation, 'arcsec')

fig, ax = scene.plot_spectra()"""),
md("""## 5. Assemble by hand

`from_components` gives the same object `from_default` would have built."""),
code("""sim = Simulation.from_components(t, s, scene, c)
base = sim.get_snr(3600, 100)['snr']
print('SNR:', round(base, 3))
assert abs(base - Simulation.from_default().get_snr(3600, 100)['snr']) < 1e-9"""),
md("""## 6. Change parameters

`update()` changes a parameter in place and the next calculation sees it. From the simulation, nested parameters are addressed with double underscores, so `sim.update(coronagraph__ppgain=100)` is the same as `sim.coronagraph.update(ppgain=100)`. An invalid value is refused and leaves the object unchanged. `sim.reset()` puts every component back to its initial state.

Two changes below, one at a time. A fainter host means a fainter planet, because the planet is defined relative to the host, so the SNR drops and the curve is no longer near its plateau. Raising `ppgain` then lifts the plateau from 10 to 100 and the SNR climbs back most of the way, but not above the default scene's: the fainter planet is photon-limited rather than speckle-limited, so a higher plateau helps less than it would for the bright host."""),
code("""sim.update(scene__star__mag=2.0)
faint = sim.get_snr(3600, 100)['snr']
print('host 2.35 mag fainter        :', round(faint, 3))
sim.update(coronagraph__ppgain=100)
faint_pp = sim.get_snr(3600, 100)['snr']
print('... and post-processing gain 100:', round(faint_pp, 3))
assert faint < faint_pp < base

try:
    sim.update(sensor__encircled_energy=1.7)
except ValueError as err:
    print('refused:', err)

sim.reset()
print('after reset:', round(sim.get_snr(3600, 100)['snr'], 3))
assert abs(sim.get_snr(3600, 100)['snr'] - base) < 1e-9"""),
md("""Notebook 03 looks at what the three coronagraph parameters do to the SNR curve."""),
])

# ---------------------------------------------------------------- 03
write("03_coronagraph_and_contrast.ipynb", [
md(f"""# 03 Coronagraph and contrast

Three parameters set the coronagraph's contribution to the noise budget:

- `raw_dh_contrast`, the raw dark-hole contrast. It sets the residual speckle rate, `speckle = host x contrast x EE` (notebook 01).
- `ppgain`, the post-processing gain. Speckles that survive post-processing form a systematic floor `M = speckle / ppgain` that grows linearly with time, unlike photon noise. `ppgain` is a number you supply, not something the calculator predicts, and it carries no random-noise cost of its own.
- `separation`, the planet's angular distance from the star in arcsec. It sets the off-axis throughput of the focal-plane mask.

Because `M` grows like t while photon noise grows like sqrt(t), the SNR curve flattens into a plateau at `source / M`. With the default scene the planet and speckle rates are equal, so the plateau sits at SNR = ppgain = 10. 
{REQ_SHORT}"""),
code("""import astropy.units as u
from esc_etc import Simulation, use_lazuli_style
use_lazuli_style()

sim = Simulation.from_default(hoststarmag=-0.353, planetdeltamag=20,
                              contrast=1e-8, ppgain=10, separation=0.4)"""),
md("""## 1. Raw dark-hole contrast

`plot_snr_vs_time(sweep=...)` draws one SNR curve per value of any parameter you could pass to `update()`, and restores the original value afterwards. Better contrast lowers the speckle rate and therefore raises the plateau: at 1e-9 the ceiling is 100, at 1e-7 it is 1, and no integration time gets past it."""),
code("""fig, ax = sim.plot_snr_vs_time(sweep={'coronagraph__raw_dh_contrast': [1e-7, 1e-8, 1e-9]})
ax.set_title('SNR vs time for three raw contrasts');

snr_at_1h = {}
for cval in [1e-7, 1e-8, 1e-9]:
    sim.update(coronagraph__raw_dh_contrast=cval)
    snr_at_1h[cval] = sim.get_snr(3600, 100)['snr']
    print(f'contrast {cval:.0e}: SNR(1 h) = {snr_at_1h[cval]:.3f}')
sim.reset()
assert snr_at_1h[1e-7] < snr_at_1h[1e-8] < snr_at_1h[1e-9]
assert snr_at_1h[1e-7] < 1.0 + 1e-6      # pinned at the plateau"""),
md("""## 2. Post-processing gain

`ppgain` moves the plateau without changing the photon-limited rise. At ppgain 1 the floor equals the speckle rate itself and the SNR never exceeds 1 for this scene."""),
code("""fig, ax = sim.plot_snr_vs_time(sweep={'coronagraph__ppgain': [1, 10, 100]})
ax.set_title('SNR vs time for three post-processing gains');

for g in [1, 10, 100]:
    sim.update(coronagraph__ppgain=g)
    print(f'ppgain {g:3d}: SNR(1 h) = {sim.get_snr(3600, 100)["snr"]:.3f}')
sim.reset()"""),
md("""## 3. Separation and off-axis throughput

The focal-plane mask attenuates the planet as well as the star. `off_axis_throughput` is the fraction of planet light transmitted at a given separation; it rises from near zero inside the inner working angle toward a plateau. The throughput multiplies every rate in the aperture, so moving the planet in or out changes the photon-limited part of the curve but not the plateau, which is a ratio of two rates with the same factor."""),
code("""for sep in [0.1, 0.2, 0.4]:
    print(f'separation {sep} arcsec: off-axis throughput {sim.coronagraph.off_axis_throughput(sep):.3f}')
assert abs(sim.coronagraph.off_axis_throughput(0.4) - 0.58) < 0.01

fig, ax = sim.coronagraph.plot_offaxis_throughput()
ax.set_title('Focal-plane mask throughput');

fig, ax = sim.plot_snr_vs_time(sweep={'coronagraph__separation': [0.1, 0.2, 0.4]})
ax.set_title('SNR vs time for three separations');"""),
md("""## 4. Reference-star subtraction

With `subtraction="rdi"` a reference star `ref_brightness_ratio` times brighter than the host is observed for `ref_time_ratio` times the science time and subtracted. Its photon noise adds to the budget and the reference time is charged, so `charged_time` is larger than `science_time`. The defaults are `ref_brightness_ratio=1` and `ref_time_ratio=1`, so one hour of science is charged as two. Roll or ADI self-subtraction is not modelled."""),
code("""sim.update(coronagraph__subtraction='rdi')
out = sim.get_snr(3600, 100)
print('SNR with RDI   :', round(out['snr'], 3))
print('science time   :', out['science_time'], '| charged time:', out['charged_time'])
sim.reset()"""),
md("""Notebook 04 covers the time axis in more detail: frame times, read noise, and saturation."""),
])

# ---------------------------------------------------------------- 04
write("04_integration_time_snr_saturation.ipynb", [
md(f"""# 04 Integration time, frames and saturation

The calculator treats an observation as `n_reads = ceil(total_time / frame_time)` detector frames. The frame time therefore sets the read-noise contribution and is bounded above by saturation. This notebook shows both effects and how to check them.

{REQ_SHORT}"""),
code("""import numpy as np
import astropy.units as u
import matplotlib.pyplot as plt
from esc_etc import Simulation, use_lazuli_style
use_lazuli_style()

sim = Simulation.from_default(hoststarmag=-0.353, planetdeltamag=20,
                              contrast=1e-8, ppgain=10, separation=0.4)"""),
md("""## 1. Frame time and read noise

Shorter frames mean more reads and more read noise, which matters most early in the integration before the speckle floor takes over. A single 600 s frame is allowed here because the saturation time is about 35,000 s (section 3); for a brighter host that will not be true. `plot_snr_vs_time` accepts `ax=` and `label=`, so several calls can share one axis."""),
code("""fig, ax = plt.subplots()
for ft in [10, 100, 1000]:
    sim.plot_snr_vs_time(frame_time=ft * u.s, ax=ax, label=f'frame time {ft} s')
ax.set_title('Read noise through the frame time');

t_short = sim.get_snr(600, 10)['snr']
t_long = sim.get_snr(600, 600)['snr']
print('SNR in 600 s with 10 s frames :', round(t_short, 3))
print('SNR in 600 s with one frame   :', round(t_long, 3))
assert t_short < t_long"""),
md("""## 2. Inverting for integration time

`get_int_time_for_snr` returns both the exact (`int_time_continuous`) and the frame-rounded (`int_time`) solution. It returns NaN when the target is above the plateau, which is the calculator telling you that no amount of time will get there."""),
code("""snr_1h = sim.get_snr(3600, 100)['snr']
back = sim.get_int_time_for_snr(snr_1h, frame_time=100)
print('round trip   :', back['int_time'][0])
assert abs(back['int_time'][0].value - 3600) < 1

unreachable = sim.get_int_time_for_snr(20, frame_time=100)
print('time to SNR 20 with a plateau at 10:', unreachable['int_time_continuous'][0])
assert np.isnan(unreachable['int_time_continuous'][0].value)"""),
md("""## 3. Saturation

`saturation_time` is the frame time at which the brightest pixel in the planet's photometric aperture reaches `headroom x well_depth`. It counts the planet, the speckles at the dark-hole contrast, the backgrounds and dark current. It does not model the stellar core behind the mask or the bright ring near the inner working angle, so for a bright host the true detector-safe frame time can be much shorter than this number. `is_saturated` compares a frame time against it, and `get_snr` warns when a frame would saturate."""),
code("""import warnings

t_sat = sim.saturation_time()
print('saturation time        :', t_sat)
print('is_saturated(100 s)    :', bool(sim.is_saturated(100)))
print('is_saturated(2 x t_sat):', bool(sim.is_saturated(2 * t_sat)))

with warnings.catch_warnings(record=True) as caught:
    warnings.simplefilter('always')
    sim.get_snr(total_time=4 * t_sat, frame_time=2 * t_sat)
print('warning from get_snr   :', str(caught[0].message)[:60], '...')
assert caught"""),
md("""That is the whole calculator. The user guide in the documentation has the equations behind each term, and `esc_etc.plotting` has the raw-array form of every plot used here."""),
])
