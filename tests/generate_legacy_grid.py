# tests/generate_legacy_grid.py
"""One-off: capture current esc_calc_snr outputs over a grid for equivalence testing.
Run once with the pre-refactor engine; the committed JSON is the cross-check baseline."""
import json
import os
import esc_etc.ExposureTimeSNRCalculatorESC as esc_mod

GRID = [
    dict(exp_time=3600, int_time=100, separation=0.4, contrast=1e-8, ppgain=10),
    dict(exp_time=600, int_time=10, separation=0.2, contrast=1e-8, ppgain=10),
    dict(exp_time=3600, int_time=100, separation=0.4, contrast=1e-9, ppgain=10),
    dict(exp_time=3600, int_time=100, separation=0.4, contrast=1e-8, ppgain=100),
    dict(exp_time=1800, int_time=60, separation=0.3, contrast=1e-8, ppgain=10, planetdeltamag=22),
    dict(exp_time=3600, int_time=100, separation=0.4, contrast=1e-8, ppgain=10, hoststarmag=2.0),
    dict(exp_time=3600, int_time=100, separation=0.4, contrast=1e-8, ppgain=10, bg_flux=21.0),
]

def main():
    records = []
    for params in GRID:
        snr, esc = esc_mod.esc_calc_snr(verbose=False, plot=False, **params)
        records.append(dict(
            params=params,
            snr=float(snr),
            source_counts=float(esc.source_counts.value),
            sky_counts=float(esc.sky_counts.value),
            speckle_counts=float(esc.speckle_counts.value),
            exozodi_counts=float(esc.exozodi_counts.value),
            num_psf_pixels=float(esc.num_psf_pixels.value),
        ))
    out = os.path.join(os.path.dirname(__file__), "test_data", "legacy_snr_grid.json")
    os.makedirs(os.path.dirname(out), exist_ok=True)
    with open(out, "w") as f:
        json.dump(records, f, indent=2)
    print(f"wrote {len(records)} records to {out}")

if __name__ == "__main__":
    main()
