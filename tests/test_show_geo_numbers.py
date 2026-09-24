from geo_analysis.show_geo_numbers import (
    DEFAULTS,
    _values_from_args,
    build_parser,
    calculate_numbers,
)


def test_calculate_numbers_uses_custom_values():
    values = calculate_numbers(
        lat1=0.0,
        lon1=0.0,
        lat2=0.0,
        lon2=1.0,
        wind_direction=90.0,
        distance_km=10.0,
        proximity_score=1.0,
        air_quality_anomaly=0.0,
        temporal_correlation=0.0,
        downwind_tolerance=5.0,
    )

    assert values["bearing"] == 90.0
    assert values["downwind"] is True
    assert values["alignment"] == 1.0
    assert values["risk"] == 0.55


def test_cli_arguments_override_defaults():
    args = build_parser().parse_args(["--lat1", "0", "--lon1", "1"])

    values = _values_from_args(args)

    assert values["lat1"] == 0.0
    assert values["lon1"] == 1.0
    assert values["lat2"] == DEFAULTS["lat2"]


def test_interactive_mode_accepts_enter_for_defaults(monkeypatch):
    args = build_parser().parse_args(["--interactive"])
    monkeypatch.setattr("builtins.input", lambda _: "")

    assert _values_from_args(args) == DEFAULTS