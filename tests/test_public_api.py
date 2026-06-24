def test_public_exports():
    import esc_etc
    for name in ["Simulation", "Telescope", "Sensor", "Scene", "SceneElement",
                 "Coronagraph", "get_scene", "AnalyticCoronagraphNoiseModel",
                 "CountRates", "esc_calc_snr", "Observatory"]:
        assert hasattr(esc_etc, name), f"missing export: {name}"
