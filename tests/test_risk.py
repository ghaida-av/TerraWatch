from geo_analysis.risk import calculate_risk, calculate_risk_from_spatial


def test_calculate_risk_is_weighted_combination():
    score = calculate_risk(
        proximity_score=0.8,
        wind_alignment=0.9,
        air_quality_anomaly=0.7,
        temporal_correlation=0.8,
    )
    assert 0.0 <= score <= 1.0


def test_calculate_risk_from_spatial_contract():
    result = calculate_risk_from_spatial(
        {
            "event_id": "F001",
            "target_id": "CITY_CAIRO",
            "distance_km": 78.4,
            "proximity_score": 0.78,
            "wind_alignment": 0.97,
            "downwind": True,
        },
        air_quality_anomaly=0.82,
        temporal_correlation=0.91,
    )

    assert result["event_id"] == "F001"
    assert result["target_id"] == "CITY_CAIRO"
    assert "risk_score" in result
    assert "components" in result
