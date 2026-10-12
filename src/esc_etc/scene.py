"""Observable scene for the ESC ETC: host star, planet, zodi, exozodi.

Planet flux model (issue #13): ``planet.spectrum`` is a spectral *shape*,
normalized ``planet.deltamag`` magnitudes fainter than the host in
``planet.deltamag_band`` (None = the ESC sensor bandpass; a synphot filter name
such as ``"johnson_v"``; or a SpectralElement), in the host's magnitude system,
then observed through the ESC bandpass. With the default flat shape and ESC-band
reference this reduces to ``R_host * 10**(-0.4 * deltamag)``. ``planet.mag`` is
unused -- the planet's brightness is always host + deltamag.

Reference bands (issue #14): every magnitude carries the band it is quoted in.
``band`` is None for the ESC sensor bandpass, a synphot filter name such as
``"johnson_v"`` for catalog photometry, or a SpectralElement. Spectra are
normalized in that band, then observed through the ESC bandpass. Defaults:
host and exozodi in the ESC band, zodi surface brightness in Johnson V.

Backgrounds use the zodi profile file from the telescope config.
"""

from synphot import SourceSpectrum, units as su
from synphot.models import ConstFlux1D
from astropy import units as u

from .meta import _MetaHolder_

MAG_SYSTEMS = {
    "vega": su.VEGAMAG,
    su.VEGAMAG: su.VEGAMAG,
    "AB": u.ABmag,
    "ABmag": u.ABmag,
    u.ABmag: u.ABmag,
}


def mag_units(mag_system):
    """Vega or AB magnitude unit for a ``mag_system`` spelling; loud otherwise."""
    try:
        return MAG_SYSTEMS[mag_system]
    except (KeyError, TypeError):
        raise ValueError(
            f"mag_system must be 'vega' or 'AB', got {mag_system!r}"
        ) from None


class SceneElement(_MetaHolder_):
    def __init__(
        self,
        name,
        spectrum,
        mag,
        mag_system="vega",
        deltamag=None,
        deltamag_band=None,
        band=None,
    ):
        self._mutable_parameters = [
            "spectrum",
            "mag",
            "mag_system",
            "deltamag",
            "deltamag_band",
            "band",
        ]
        self.name = name
        self._init_meta(
            spectrum=spectrum,
            mag=mag,
            mag_system=mag_system,
            deltamag=deltamag,
            deltamag_band=deltamag_band,
            band=band,
        )
        self._on_update([])

    def _on_update(self, updated_keys):
        mag_units(self.mag_system)


class Scene(_MetaHolder_):
    """The host ``star``, the ``planet``, and the ``zodi`` / ``exozodi``
    backgrounds, each a :class:`SceneElement`."""

    def __init__(self, star, planet, zodi, exozodi):
        self._mutable_parameters = []
        self.star = star
        self.planet = planet
        self.zodi = zodi
        self.exozodi = exozodi
        self._init_meta()

    def plot_spectra(self, **kw):
        """See :func:`esc_etc.plotting.plot_spectra`."""
        from . import plotting

        return plotting.plot_spectra(self, **kw)


def get_scene(
    telescope,
    hoststarmag=-0.353,
    planetdeltamag=20.0,
    bg_flux=22.5,
    exobg_flux=21.0,
    mag_system="vega",
    background_file=None,
    hoststar_band=None,
):
    """Build a Scene from magnitudes.

    - ``hoststarmag``: host magnitude in ``hoststar_band`` (None = ESC band;
      ``"johnson_v"`` for a catalog V magnitude).
    - ``planetdeltamag``: planet fainter than the host by this much in the ESC
      band (change via ``planet.deltamag_band``).
    - ``bg_flux``: zodi surface brightness, mag/arcsec^2 in Johnson V.
    - ``exobg_flux``: exozodi DELTA magnitude; surface brightness is
      ``hoststarmag + exobg_flux`` mag/arcsec^2 in the ESC band.
    - ``mag_system``: ``"vega"`` or ``"AB"``, applied to every magnitude above.
    """
    flat = SourceSpectrum(ConstFlux1D, amplitude=hoststarmag * u.ABmag)
    star = SceneElement(
        "star", flat, mag=hoststarmag, mag_system=mag_system, band=hoststar_band
    )
    # planet.mag is ignored: brightness is host + deltamag in the ESC band.
    planet = SceneElement(
        "planet", flat, mag=None, mag_system=mag_system, deltamag=planetdeltamag
    )
    bg_path = (
        background_file if background_file is not None else telescope.zodi_profile_path
    )
    zodi_spectrum = SourceSpectrum.from_file(bg_path)
    zodi = SceneElement(
        "zodi", zodi_spectrum, mag=bg_flux, mag_system=mag_system, band="johnson_v"
    )
    exozodi = SceneElement(
        "exozodi", zodi_spectrum, mag=hoststarmag + exobg_flux, mag_system=mag_system
    )
    return Scene(star, planet, zodi, exozodi)
