"""Ten ground-truth scenarios.

Each scenario states the physical situation and what a domain-sensible assessment must look like. Expectations
are reasoned from first principles (is the smoke actually heading for the town? is the data even there?), NOT
copied from whatever the code currently outputs. A scenario with `known_issue` documents a real defect: it is
expected to fail today, and the suite turns red (strict xfail) the moment someone fixes it so the note gets removed.
"""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Callable, Dict, List, Optional

from data.schemas.models import Evidence
from evals import builders as b

RISING_PM25 = [30, 32, 35, 40, 48, 58, 70]
FLAT_CLEAN = [10, 10, 10, 10]

# Bearing fire -> town is 225 deg (fire is NE of town). A wind coming FROM 45 deg carries smoke toward the town.
TOWARD_TOWN_WIND_FROM = 45
AWAY_FROM_TOWN_WIND_FROM = 225


@dataclass
class Scenario:
    id: str
    title: str
    rationale: str
    evidence: Callable[[], List[Evidence]]
    expect: Dict[str, Any]
    question: str = "What environmental risks exist?"
    known_issue: Optional[str] = None


SCENARIOS: List[Scenario] = [
    Scenario(
        "S01_smoke_event", "Fire upwind of town, smoke arriving, PM2.5 climbing",
        "Close fire, wind carrying smoke to the town, air quality rising after detection: the textbook incident.",
        lambda: [b.weather(24, TOWARD_TOWN_WIND_FROM), b.fire(20, 225), b.air_quality(80, RISING_PM25)],
        {"level_in": ["HIGH", "CRITICAL"], "downwind": True, "fire_count": 1,
         "findings_contain": ["closest at 20"], "gaps_empty": True},
    ),
    Scenario(
        "S02_clean_baseline", "No fires, clean air",
        "Satellite reachable and reports zero hotspots (absence is evidence); air is clean. Must be LOW.",
        lambda: [b.weather(10, 200), b.fire(None), b.air_quality(8, [8, 9, 8, 8])],
        {"level_in": ["LOW"], "score_max": 0.10, "fire_count": 0,
         "summary_contains": ["stable baseline"], "findings_contain": ["Zero active thermal hotspots"]},
    ),
    Scenario(
        "S03_fire_upwind_of_smoke", "Close fire but wind blows the smoke away from town",
        "Same fire as S01 but the wind direction is reversed. Smoke is heading away, so it must NOT be downwind "
        "and must not rate HIGH/CRITICAL.",
        lambda: [b.weather(24, AWAY_FROM_TOWN_WIND_FROM), b.fire(20, 225), b.air_quality(10, FLAT_CLEAN)],
        {"level_in": ["LOW", "MODERATE"], "downwind": False, "findings_contain": ["upwind or crosswind"]},
    ),
    Scenario(
        "S04_far_fire_clean_air", "Fire 140 km away, downwind, air still clean",
        "Distant fire and no exposure yet: worth watching, not HIGH.",
        lambda: [b.weather(24, TOWARD_TOWN_WIND_FROM), b.fire(140, 225), b.air_quality(10, FLAT_CLEAN)],
        {"level_in": ["LOW", "MODERATE"]},
        known_issue="temporal_correlation scores 1.0 from timestamps alone (fire detected ~2 h before the AQ reading) "
                    "even when PM2.5 never rose, so a clean-air town 140 km from a fire rates HIGH.",
    ),
    Scenario(
        "S05_calm_wind_close_fire", "Fire 10 km away but the air is almost still",
        "With ~0 km/h wind, smoke does not travel in a direction, so wind alignment should not add full weight.",
        lambda: [b.weather(0.5, TOWARD_TOWN_WIND_FROM), b.fire(10, 225), b.air_quality(10, FLAT_CLEAN)],
        {"level_in": ["MODERATE", "HIGH"]},
        known_issue="wind speed is ignored: a 0.5 km/h breeze counts as perfectly aligned transport.",
    ),
    Scenario(
        "S06_downwind_clean_air", "Close fire downwind but PM2.5 still normal (early warning)",
        "No exposure measured yet: an early warning (MODERATE/HIGH), not CRITICAL.",
        lambda: [b.weather(24, TOWARD_TOWN_WIND_FROM), b.fire(25, 225), b.air_quality(10, FLAT_CLEAN)],
        {"level_in": ["MODERATE", "HIGH"], "downwind": True},
        known_issue="same root cause as S04: temporal_correlation is not gated on an actual PM2.5 increase.",
    ),
    Scenario(
        "S07_dust_no_fire", "PM2.5 spike with no fire (e.g. dust storm)",
        "Air-quality hazard exists without any fire; it must be surfaced as an indicator.",
        lambda: [b.weather(20, 90), b.fire(None), b.air_quality(90, [20, 20, 20, 20])],
        {"level_in": ["MODERATE", "HIGH"], "fire_count": 0, "findings_contain": ["PM2.5 measured at 90"],
         "indicators_contain": ["Unhealthy particulate"]},
    ),
    Scenario(
        "S08_all_sources_down", "Every data source failed",
        "No data is not good news. Confidence must be low, the report must say 'insufficient data', and it must "
        "never claim zero fires or calm winds.",
        lambda: [b.failed("weather", "open-meteo"), b.failed("fire", "nasa_firms"), b.failed("air_quality", "openaq")],
        {"confidence_max": 0.30, "summary_contains": ["Insufficient data"],
         "summary_absent": ["stable baseline"], "findings_absent": ["Zero active thermal hotspots", "Wind recorded"],
         "gaps_contain": ["fire:error", "weather:error", "air_quality:error"]},
    ),
    Scenario(
        "S09_no_air_quality_coverage", "Fire downwind, but no air-quality station covers the town",
        "Missing AQ coverage must be reported as a gap, not as clean air, and the summary must say it is incomplete.",
        lambda: [b.weather(24, TOWARD_TOWN_WIND_FROM), b.fire(40, 225), b.failed("air_quality", "openaq", "no_data")],
        {"downwind": True, "gaps_contain": ["air_quality:no_data"], "findings_contain": ["No active in-situ"],
         "summary_contains": ["incomplete"], "summary_absent": ["stable baseline"]},
    ),
    Scenario(
        "S10_modeled_air_quality", "PM2.5 comes from a model, not a sensor",
        "Modeled values are weaker evidence: confidence must drop below a fully-observed run and the finding "
        "must say the value is modeled.",
        lambda: [b.weather(24, TOWARD_TOWN_WIND_FROM), b.fire(30, 225), b.air_quality(60, [30, 32, 35, 40], modeled=True)],
        {"confidence_max": 0.90, "findings_contain": ["modeled estimate"]},
    ),
]
