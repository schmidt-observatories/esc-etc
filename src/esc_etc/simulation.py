"""Top-level ESC ETC orchestrator: composes Telescope, Sensor, Scene, Coronagraph.

count_rate_components extracts Observatory.make_observation: it normalizes the
host on the FPM-free Sensor.bandpass, derives planet/speckle by scaling, computes
zodi/exozodi with the resel factor, then multiplies EVERY rate by the flat FPM
throughput k = coronagraph.off_axis_throughput (plan physics-fact #1).

Every SNR term is evaluated in ONE extraction aperture, Omega = telescope.resel
= pi (lambda/2D)^2 (issue #10):

    R_planet  = R_host * 10^(-0.4 dmag) * k     k = planet throughput into Omega
    R_speckle = R_host * C * k                  C = raw contrast, see Coronagraph
    R_zodi    = SB_zodi * Omega * k             (exozodi likewise)
    N_pix     = Omega / plate_scale^2           (dark current, read noise)

k on the diffuse terms stands in for the diffuse-background transmission.
ponytail: assumed equal to the point-source core throughput; split it out when
the FPM data records total transmission separately.
"""
from astropy import units as u
from synphot import Observation, SourceSpectrum, SpectralElement, units as su

from .meta import _MetaHolder_
from .telescope import Telescope
from .sensor import Sensor
from .scene import Scene, get_scene
from .coronagraph import Coronagraph
from .noise import CountRates, AnalyticCoronagraphNoiseModel

FORCE = None


class Simulation(_MetaHolder_):
    def __init__(self, telescope, sensor, scene, coronagraph, noise_model=None):
        self._mutable_parameters = []
        self.telescope = telescope
        self.sensor = sensor
        self.scene = scene
        self.coronagraph = coronagraph
        self.noise_model = noise_model or AnalyticCoronagraphNoiseModel()
        self._vega = None
        self._johnson_v = None
        self._init_meta()

    @classmethod
    def from_components(cls, telescope, sensor, scene, coronagraph, noise_model=None):
        return cls(telescope, sensor, scene, coronagraph, noise_model)

    @classmethod
    def from_default(cls, hoststarmag=-0.353, planetdeltamag=20.0, contrast=1e-8,
                     ppgain=10, separation=0.4, bg_flux=22.5, exobg_flux=21.0,
                     arm="arm_a"):
        telescope = Telescope.from_default(arm=arm)
        sensor = Sensor.from_default(telescope, arm=arm)
        scene = get_scene(telescope, hoststarmag=hoststarmag,
                          planetdeltamag=planetdeltamag, bg_flux=bg_flux,
                          exobg_flux=exobg_flux)
        coronagraph = Coronagraph.from_default(
            telescope, raw_dh_contrast=contrast, ppgain=ppgain, separation=separation,
            arm=arm)
        return cls(telescope, sensor, scene, coronagraph)

    def _normalize_units(self, mag_system):
        if mag_system in ("vega", su.VEGAMAG):
            return su.VEGAMAG
        if mag_system in ("AB", "ABmag", u.ABmag):
            return u.ABmag
        raise NotImplementedError(f"flux units {mag_system!r} not implemented")

    def count_rate_components(self):
        if self._vega is None:
            self._vega = SourceSpectrum.from_vega()
        if self._johnson_v is None:
            self._johnson_v = SpectralElement.from_filter("johnson_v")
        vega = self._vega
        bp = self.sensor.bandpass
        area = self.telescope.surface
        resel = self.telescope.resel
        k = self.coronagraph.off_axis_throughput(self.coronagraph.separation)

        star = self.scene.star
        norm_units = self._normalize_units(star.mag_system)
        if norm_units is su.VEGAMAG:
            host_sp = star.spectrum.normalize(star.mag * su.VEGAMAG, bp,
                                              vegaspec=vega, force=FORCE)
        else:
            host_sp = star.spectrum.normalize(star.mag * u.ABmag, bp, force=FORCE)
        host_obs = Observation(host_sp, bp, force=FORCE)
        host_countrate = host_obs.countrate(area=area) * u.electron / u.ct

        planet_scale = 10 ** (-0.4 * self.scene.planet.deltamag)
        source = host_countrate * planet_scale * k
        speckle = host_countrate * self.coronagraph.speckle_scale() * k

        zodi_norm_units = self._normalize_units(self.scene.zodi.mag_system)
        if zodi_norm_units is su.VEGAMAG:
            zodi_rn = self.scene.zodi.spectrum.normalize(
                self.scene.zodi.mag * su.VEGAMAG, self._johnson_v, vegaspec=vega, force=FORCE)
        else:
            zodi_rn = self.scene.zodi.spectrum.normalize(
                self.scene.zodi.mag * u.ABmag, self._johnson_v, force=FORCE)
        zodi_obs = Observation(zodi_rn, bp, force=FORCE)
        zodi = zodi_obs.countrate(area=area) * u.electron / u.ct * resel / u.arcsec ** 2 * k

        exo_norm_units = self._normalize_units(self.scene.exozodi.mag_system)
        if exo_norm_units is su.VEGAMAG:
            exo_rn = self.scene.exozodi.spectrum.normalize(
                self.scene.exozodi.mag * su.VEGAMAG, bp, vegaspec=vega, force=FORCE)
        else:
            exo_rn = self.scene.exozodi.spectrum.normalize(
                self.scene.exozodi.mag * u.ABmag, bp, force=FORCE)
        exo_obs = Observation(exo_rn, bp, force=FORCE)
        exozodi = exo_obs.countrate(area=area) * u.electron / u.ct * resel / u.arcsec ** 2 * k

        # host is the POST-FPM (k-scaled) host count rate, NOT the unattenuated
        # stellar flux. Consumers (e.g. contrast estimation) must account for the
        # applied FPM throughput k if they need the raw stellar rate.
        return CountRates(source=source, zodi=zodi, exozodi=exozodi,
                          speckle=speckle, host=host_countrate * k)

    def get_snr(self, total_time, frame_time):
        rates = self.count_rate_components()
        return self.noise_model.snr(rates, self.sensor, self.coronagraph,
                                    total_time, frame_time)

    def get_int_time_for_snr(self, snr, frame_time):
        rates = self.count_rate_components()
        return self.noise_model.int_time_for_snr(snr, rates, self.sensor,
                                                 self.coronagraph, frame_time)

    def saturation_time(self):
        """Frame time at which the brightest dark-hole pixel reaches
        ``sensor.headroom * sensor.well_depth``.

        Planet and speckle put ``sensor.peak_pixel_fraction`` of their
        in-aperture rate on the peak pixel; zodi and exozodi spread uniformly
        over ``num_psf_pixels``; dark current adds per pixel. The occulted host
        is out of scope: this is the dark-hole science ROI, not the stellar
        core behind the FPM.
        """
        r = self.count_rate_components()
        s = self.sensor
        peak = ((r.source + r.speckle) * s.peak_pixel_fraction
                + (r.zodi + r.exozodi) / s.num_psf_pixels.value) / u.pix + s.dark_current
        return (s.headroom * s.well_depth / peak).to(u.s)

    def is_saturated(self, frame_time):
        return frame_time > self.saturation_time()
