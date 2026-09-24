from geo_analysis.temporal import find_events_in_window, temporal_correlation, time_difference


def test_time_difference_uses_hours():
    assert time_difference("2026-09-21T12:00:00Z", "2026-09-21T14:00:00Z") == 2.0


def test_find_events_in_window_filters_records():
    events = [
        {"id": "fire", "time": "2026-09-21T12:00:00Z"},
        {"id": "wind", "time": "2026-09-21T13:00:00Z"},
        {"id": "pm25", "time": "2026-09-21T14:00:00Z"},
    ]
    found = find_events_in_window(events, "2026-09-21T13:00:00Z", window_hours=2)
    assert [event["id"] for event in found] == ["wind", "fire", "pm25"] or [event["id"] for event in found] == ["fire", "wind", "pm25"]


def test_temporal_correlation_scores_expected_delay():
    score = temporal_correlation("2026-09-21T12:00:00Z", "2026-09-21T14:00:00Z", expected_delay_hours=2, tolerance_hours=6)
    assert score == 1.0
