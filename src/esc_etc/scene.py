"""Observable scene for the ESC ETC: host star, planet, zodi, exozodi.

Planet flux model (issue #13): ``planet.spectrum`` is a spectral *shape*,
normalized ``planet.deltamag`` magnitudes fainter than the host in
``planet.deltamag_band`` (None = the ESC sensor bandpass; a synphot filter name
such as ``"johnson_v"``; or a SpectralElement), in the host's magnitude system,
then observed through the ESC bandpass. With the default flat shape and ESC-band
reference this reduces to ``R_host * 10**(-0.4 * deltamag)``. ``planet.mag`` is
unused -- the planet's brightness is always host + deltamag.

Backgrounds use the zodi profile file from the telescope config.
"""
from synphot import SourceSpectrum
from synphot.models import ConstFlux1D
from astropy import units as u

from .meta import _MetaHolder_


class SceneElement(_MetaHolder_):
    def __init__(self, name, spectrum, mag, mag_system="vega", deltamag=None,
                 deltamag_band=None):
        self._mutable_parameters = ["spectrum", "mag", "mag_system", "deltamag",
                                    "deltamag_band"]
        self.name = name
        self._init_meta(spectrum=spectrum, mag=mag, mag_system=mag_system,
                        deltamag=deltamag, deltamag_band=deltamag_band)


class Scene(_MetaHolder_):
    def __init__(self, star, planet, zodi, exozodi):
        self._mutable_parameters = []
        self.star = star
        self.planet = planet
        self.zodi = zodi
        self.exozodi = exozodi
        self._init_meta()


def get_scene(telescope, hoststarmag=-0.353, planetdeltamag=20.0, bg_flux=22.5,
              exobg_flux=21.0, mag_system="vega", background_file=None):
    """Build a Scene from host magnitude + planet delta-mag + background mags."""
    flat = SourceSpectrum(ConstFlux1D, amplitude=hoststarmag * u.ABmag)
    star = SceneElement("star", flat, mag=hoststarmag, mag_system=mag_system)
    # planet.mag is ignored: brightness is host + deltamag in the ESC band.
    planet = SceneElement("planet", flat, mag=None, mag_system=mag_system,
                          deltamag=planetdeltamag)
    bg_path = background_file if background_file is not None else telescope.zodi_profile_path
    zodi_spectrum = SourceSpectrum.from_file(bg_path)
    zodi = SceneElement("zodi", zodi_spectrum, mag=bg_flux, mag_system=mag_system)
    exozodi = SceneElement("exozodi", zodi_spectrum, mag=hoststarmag + exobg_flux,
                           mag_system=mag_system)
    return Scene(star, planet, zodi, exozodi)
