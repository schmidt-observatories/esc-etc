"""Top-level ESC ETC orchestrator: composes Telescope, Sensor, Scene, Coronagraph.

count_rate_components extracts Observatory.make_observation: it normalizes the
host on the FPM-free Sensor.bandpass, derives planet/speckle by scaling, computes
zodi/exozodi with the resel factor, then multiplies EVERY rate by the flat FPM
throughput k = coronagraph.off_axis_throughput (plan physics-fact #1).

Every SNR term is evaluated in ONE photometric aperture, chosen by
``Sensor.aperture`` (the resel, Omega = pi (lambda/2D)^2, by default; issue #10)
with encircled energy EE = ``Sensor.ee_fraction`` for point sources::

    R_planet  = R_planet,ref * k * EE           planet spectrum normalised dmag
                                                fainter than the host; k = FPM
                                                off-axis throughput
    R_speckle = R_host * C * k * EE             C = raw contrast, see Coronagraph
    R_zodi    = SB_zodi * Omega * k             (exozodi likewise)
    N_pix     = Omega / plate_scale^2           (dark current, read noise)

k on the diffuse terms stands in for the diffuse-background transmission.
ponytail: assumed equal to the point-source core throughput; split it out when
the FPM data records total transmission separately.
"""

import warnings

import numpy as np
from astropy import units as u
from synphot import Observation, SourceSpectrum, SpectralElement, units as su

from .meta import _MetaHolder_
from .telescope import Telescope
from .sensor import DEFAULT_FILTER, Sensor
from .scene import get_scene, mag_units
from .coronagraph import Coronagraph
from .noise import CountRates, AnalyticCoronagraphNoiseModel
from . import plotting

FORCE = None


class Simulation(_MetaHolder_):
    """A telescope, sensor, scene and coronagraph, turned into SNR and time.

    Build one with :meth:`from_default` or :meth:`from_components`. Change
    parameters with ``update(child__param=...)`` and put everything back with
    ``reset()``. Times passed to the methods may be astropy quantities or plain
    numbers in seconds. Every standard plot is a ``plot_*`` method.
    """

    def __init__(self, telescope, sensor, scene, coronagraph, noise_model=None):
        self._mutable_parameters = []
        self.telescope = telescope
        self.sensor = sensor
        self.scene = scene
        self.coronagraph = coronagraph
        self.noise_model = noise_model or AnalyticCoronagraphNoiseModel()
        self._vega = None
        self._bands = {}
        self._init_meta()

    @classmethod
    def from_components(cls, telescope, sensor, scene, coronagraph, noise_model=None):
        return cls(telescope, sensor, scene, coronagraph, noise_model)

    @classmethod
    def from_default(
        cls,
        hoststarmag=-0.353,
        planetdeltamag=20.0,
        contrast=1e-8,
        ppgain=10,
        separation=0.2,
        bg_flux=22.5,
        exobg_flux=21.0,
        arm="arm_a",
        mag_system="vega",
        hoststar_band=None,
        filter=DEFAULT_FILTER,
        lifetime="eol",
    ):
        """See ``get_scene`` for what band each magnitude is quoted in.

        ``filter`` (a key of :data:`esc_etc.FILTERS` such as ``"R1"`` /
        ``"F620N"``, default :data:`esc_etc.DEFAULT_FILTER`) uses that ESC
        filter's measured curve as the full sensor bandpass and its design
        wavelength as the telescope's central wavelength. ``lifetime`` picks the
        ``"eol"`` (end of life, default) or ``"bol"`` curve set. ``filter=None``
        is the legacy option: the generic box-filter chain assembled from the
        configuration files, which has no BOL/EOL variants.
        """
        telescope = Telescope.from_default(arm=arm, filter=filter)
        sensor = Sensor.from_default(
            telescope, arm=arm, filter=filter, lifetime=lifetime
        )
        scene = get_scene(
            telescope,
            hoststarmag=hoststarmag,
            planetdeltamag=planetdeltamag,
            bg_flux=bg_flux,
            exobg_flux=exobg_flux,
            mag_system=mag_system,
            hoststar_band=hoststar_band,
        )
        coronagraph = Coronagraph.from_default(
            telescope,
            raw_dh_contrast=contrast,
            ppgain=ppgain,
            separation=separation,
            arm=arm,
        )
        return cls(telescope, sensor, scene, coronagraph)

    def _normalize(self, element, mag, band):
        """Scale ``element.spectrum`` to ``mag`` in ``band`` (Vega/AB per element)."""
        units = mag_units(element.mag_system)
        vegaspec = self._vega if units is su.VEGAMAG else None
        return element.spectrum.normalize(
            mag * units, self._band(band), vegaspec=vegaspec, force=FORCE
        )

    def _band(self, band):
        """None -> ESC bandpass; str -> synphot filter (cached); else as given."""
        if band is None:
            return self.sensor.bandpass
        if isinstance(band, str):
            if band not in self._bands:
                self._bands[band] = SpectralElement.from_filter(band)
            return self._bands[band]
        return band

    def count_rate_components(self):
        if self._vega is None:
            self._vega = SourceSpectrum.from_vega()
        vega = self._vega
        bp = self.sensor.bandpass
        area = self.telescope.surface
        omega = self.sensor.aperture_solid_angle  # noise aperture on the sky
        ee = self.sensor.ee_fraction  # point-source light inside it
        k = self.coronagraph.off_axis_throughput(self.coronagraph.separation)

        def countrate(sp):
            return (
                Observation(sp, bp, force=FORCE).countrate(area=area)
                * u.electron
                / u.ct
            )

        star = self.scene.star
        host_sp = self._normalize(star, star.mag, star.band)
        host_countrate = countrate(host_sp)

        # Planet: its own spectral shape, deltamag fainter than the host in the
        # reference band (default: the ESC band itself), observed through bp.
        planet = self.scene.planet
        host_ref_mag = (
            Observation(host_sp, self._band(planet.deltamag_band), force=FORCE)
            .effstim(mag_units(star.mag_system), vegaspec=vega)
            .value
        )
        planet_sp = self._normalize(
            planet, host_ref_mag + planet.deltamag, planet.deltamag_band
        )
        source = countrate(planet_sp) * k * ee
        speckle = host_countrate * self.coronagraph.speckle_scale() * k * ee

        zodi_el = self.scene.zodi
        zodi = (
            countrate(self._normalize(zodi_el, zodi_el.mag, zodi_el.band))
            * omega
            / u.arcsec**2
            * k
        )

        exo_el = self.scene.exozodi
        exozodi = (
            countrate(self._normalize(exo_el, exo_el.mag, exo_el.band))
            * omega
            / u.arcsec**2
            * k
        )

        # host is the POST-FPM (k-scaled) host count rate, NOT the unattenuated
        # stellar flux. Consumers (e.g. contrast estimation) must account for the
        # applied FPM throughput k if they need the raw stellar rate.
        return CountRates(
            source=source,
            zodi=zodi,
            exozodi=exozodi,
            speckle=speckle,
            host=host_countrate * k,
        )

    def _warn_if_saturated(self, frame_time, rates):
        t_sat = self._saturation_time(rates)
        if np.any(u.Quantity(frame_time, u.s) > t_sat):
            warnings.warn(
                f"frame_time {frame_time} exceeds saturation_time {t_sat:.3g}; "
                "the brightest dark-hole pixel saturates",
                stacklevel=3,
            )

    def get_snr(self, total_time, frame_time):
        """SNR after ``total_time`` on target in frames of ``frame_time``.

        Both times accept astropy quantities or plain numbers (seconds).
        Returns a dict with ``snr``, ``signal_e``, ``noise_e``,
        ``reference_noise_e``, ``science_time``, ``charged_time`` and the
        speckle floor rate ``M``. Warns when a frame would saturate.
        """
        rates = self.count_rate_components()
        self._warn_if_saturated(frame_time, rates)
        return self.noise_model.snr(
            rates, self.sensor, self.coronagraph, total_time, frame_time
        )

    def get_int_time_for_snr(self, snr, frame_time):
        """Integration time to reach ``snr`` with frames of ``frame_time``
        (quantity or seconds).

        Returns ``int_time`` (whole frames), ``int_time_continuous`` (exact)
        and the ``noise_terms`` rates. NaN when ``snr`` is above the speckle
        plateau.
        """
        rates = self.count_rate_components()
        self._warn_if_saturated(frame_time, rates)
        return self.noise_model.int_time_for_snr(
            snr, rates, self.sensor, self.coronagraph, frame_time
        )

    def saturation_time(self):
        """Frame time at which the brightest dark-hole pixel reaches
        ``sensor.headroom * sensor.well_depth``.

        Planet and speckle put ``sensor.peak_pixel_fraction`` of their
        in-aperture rate on the peak pixel; zodi and exozodi spread uniformly
        over ``num_psf_pixels``; dark current adds per pixel. The occulted host
        is out of scope: this is the dark-hole science ROI, not the stellar
        core behind the FPM.
        """
        return self._saturation_time(self.count_rate_components())

    def _saturation_time(self, r):
        s = self.sensor
        peak = (
            (r.source + r.speckle) * s.peak_pixel_fraction
            + (r.zodi + r.exozodi) / s.num_psf_pixels.value
        ) / u.pix + s.dark_current
        return (s.headroom * s.well_depth / peak).to(u.s)

    def is_saturated(self, frame_time):
        """True when a frame of ``frame_time`` (quantity or seconds) exceeds
        :meth:`saturation_time`."""
        return u.Quantity(frame_time, u.s) > self.saturation_time()

    # Plots: thin delegates to esc_etc.plotting, which documents the keywords.
    # Every one accepts ax= and returns (fig, ax); plot() returns (fig, axes).
    def plot(self, **kw):
        """2 x 3 overview; see :func:`esc_etc.plotting.plot_overview`."""
        return plotting.plot_overview(self, **kw)

    def plot_count_rates(self, **kw):
        """See :func:`esc_etc.plotting.plot_count_rates`."""
        return plotting.plot_count_rates(self, **kw)

    def plot_snr_vs_time(self, **kw):
        """See :func:`esc_etc.plotting.plot_snr_vs_time` (supports ``sweep=``)."""
        return plotting.plot_snr_vs_time(self, **kw)

    def plot_bandpass(self, **kw):
        """See :func:`esc_etc.plotting.plot_bandpass`."""
        return plotting.plot_bandpass(self.sensor, **kw)

    def plot_spectra(self, **kw):
        """See :func:`esc_etc.plotting.plot_spectra`."""
        return plotting.plot_spectra(self.scene, **kw)

    def plot_offaxis_throughput(self, **kw):
        """See :func:`esc_etc.plotting.plot_offaxis_throughput`."""
        return plotting.plot_offaxis_throughput(self.coronagraph, **kw)

    def plot_aperture(self, **kw):
        """See :func:`esc_etc.plotting.plot_aperture`."""
        return plotting.plot_aperture(self.sensor, **kw)
