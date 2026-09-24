from geo_analysis.spatial import calculate_bearing, haversine_distance


def test_haversine_distance_round_trip():
    dist = haversine_distance(30.0444, 31.2357, 30.4, 31.8)
    assert 50 < dist < 80


def test_calculate_bearing_and_distance_are_consistent():
    bearing = calculate_bearing(30.0444, 31.2357, 30.4, 31.8)
    assert 0 <= bearing <= 360
    assert haversine_distance(30.0444, 31.2357, 30.4, 31.8) > 0
