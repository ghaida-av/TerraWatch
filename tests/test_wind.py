from geo_analysis.wind import is_downwind, wind_alignment


def test_wind_alignment_normalizes_to_unit_interval():
    assert 0.0 <= wind_alignment(0.0, 0.0) <= 1.0
    assert wind_alignment(0.97, 0.0) == 0.97


def test_is_downwind_accepts_directional_inputs():
    assert is_downwind(180, 180, tolerance_deg=5) is True
    assert is_downwind(0, 180, tolerance_deg=20) is False
