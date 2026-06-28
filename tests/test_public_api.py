def test_public_exports():
    import esc_etc
    for name in ["Simulation", "Telescope", "Sensor", "Scene", "SceneElement",
                 "Coronagraph", "get_scene", "AnalyticCoronagraphNoiseModel",
                 "CountRates", "esc_calc_snr", "Observatory"]:
        assert hasattr(esc_etc, name), f"missing export: {name}"


def test_plotting_exports():
    import esc_etc
    for name in ["plot_count_rates", "plot_snr_vs_time", "plot_offaxis_throughput",
                 "plot_bandpass", "plot_spectra", "lazuli_style", "use_lazuli_style",
                 "LAZULI_COLORS", "TEAL", "RED", "AMBER", "BLUE", "GREEN", "DARKBLUE"]:
        assert hasattr(esc_etc, name), f"missing export: {name}"
