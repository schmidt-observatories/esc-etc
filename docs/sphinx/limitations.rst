Known limitations
=================

These are the open physics items a user should know about before trusting a
number. Each links to the GitHub issue that tracks it.

- **The PSF is an Airy pattern for the full 3 m pupil.** The encircled energy
  of the photometric aperture and the automatic peak-pixel fraction do not
  include the Lyot stop, which widens the PSF, or pointing jitter. Both
  lower the encircled energy, so integration times are optimistic. Whether
  the focal-plane mask throughput table is a total or an in-core throughput
  is also still open.
  `#30 <https://github.com/schmidt-observatories/esc-etc/issues/30>`_
- **The raw contrast is one number.** It does not vary with separation,
  wavelength or bandwidth, no inner or outer working angle is enforced, and
  the off-axis throughput is read from the table with the nearest point
  rather than interpolated.
  `#32 <https://github.com/schmidt-observatories/esc-etc/issues/32>`_
- **Saturation only considers the planet's aperture.** The brightest pixel
  on the detector is near the mask edge or in the leaked stellar core, where
  the contrast is far worse than in the dark hole. For a bright host the
  detector-safe frame time is much shorter than ``saturation_time()``.
  `#33 <https://github.com/schmidt-observatories/esc-etc/issues/33>`_
- **Nothing has been checked against measured data.** The detector
  parameters are digitized from the manufacturer's plots, and the vortex
  throughput curve comes from the literature. Cross-checks against measured
  detector, vortex and on-sky data are tracked in
  `#34 <https://github.com/schmidt-observatories/esc-etc/issues/34>`_.
