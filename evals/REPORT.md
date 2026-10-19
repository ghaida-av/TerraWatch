# TerraWatch evaluation report

| Scenario | Status | Level | Score | Confidence |
|---|---|---|---|---|
| S01_smoke_event | PASS | CRITICAL | 0.78 | 0.98 |
| S02_clean_baseline | PASS | LOW | 0.00 | 0.98 |
| S03_fire_upwind_of_smoke | PASS | MODERATE | 0.42 | 0.98 |
| S04_far_fire_clean_air | KNOWN | HIGH | 0.52 | 0.98 |
| S05_calm_wind_close_fire | KNOWN | CRITICAL | 0.73 | 0.98 |
| S06_downwind_clean_air | KNOWN | CRITICAL | 0.71 | 0.98 |
| S07_dust_no_fire | PASS | MODERATE | 0.25 | 0.98 |
| S08_all_sources_down | PASS | LOW | 0.00 | 0.20 |
| S09_no_air_quality_coverage | PASS | HIGH | 0.66 | 0.67 |
| S10_modeled_air_quality | PASS | CRITICAL | 0.76 | 0.90 |

## Scenario details

### S01_smoke_event: Fire upwind of town, smoke arriving, PM2.5 climbing
_Close fire, wind carrying smoke to the town, air quality rising after detection: the textbook incident._

- PASS **risk level** got CRITICAL (0.78), want HIGH/CRITICAL
- PASS **downwind flag** got True, want True
- PASS **fire count** got 1, want 1
- PASS **findings mentions 'closest at 20'**
- PASS **no data gaps** gaps=[]

### S02_clean_baseline: No fires, clean air
_Satellite reachable and reports zero hotspots (absence is evidence); air is clean. Must be LOW._

- PASS **risk level** got LOW (0.00), want LOW
- PASS **score cap** got 0.00, want <= 0.1
- PASS **fire count** got 0, want 0
- PASS **findings mentions 'Zero active thermal hotspots'**
- PASS **summary mentions 'stable baseline'**

### S03_fire_upwind_of_smoke: Close fire but wind blows the smoke away from town
_Same fire as S01 but the wind direction is reversed. Smoke is heading away, so it must NOT be downwind and must not rate HIGH/CRITICAL._

- PASS **risk level** got MODERATE (0.42), want LOW/MODERATE
- PASS **downwind flag** got False, want False
- PASS **findings mentions 'upwind or crosswind'**

### S04_far_fire_clean_air: Fire 140 km away, downwind, air still clean
_Distant fire and no exposure yet: worth watching, not HIGH._

- FAIL **risk level** got HIGH (0.52), want LOW/MODERATE

> **Known issue:** temporal_correlation scores 1.0 from timestamps alone (fire detected ~2 h before the AQ reading) even when PM2.5 never rose, so a clean-air town 140 km from a fire rates HIGH.

### S05_calm_wind_close_fire: Fire 10 km away but the air is almost still
_With ~0 km/h wind, smoke does not travel in a direction, so wind alignment should not add full weight._

- FAIL **risk level** got CRITICAL (0.73), want MODERATE/HIGH

> **Known issue:** wind speed is ignored: a 0.5 km/h breeze counts as perfectly aligned transport.

### S06_downwind_clean_air: Close fire downwind but PM2.5 still normal (early warning)
_No exposure measured yet: an early warning (MODERATE/HIGH), not CRITICAL._

- FAIL **risk level** got CRITICAL (0.71), want MODERATE/HIGH
- PASS **downwind flag** got True, want True

> **Known issue:** same root cause as S04: temporal_correlation is not gated on an actual PM2.5 increase.

### S07_dust_no_fire: PM2.5 spike with no fire (e.g. dust storm)
_Air-quality hazard exists without any fire; it must be surfaced as an indicator._

- PASS **risk level** got MODERATE (0.25), want MODERATE/HIGH
- PASS **fire count** got 0, want 0
- PASS **findings mentions 'PM2.5 measured at 90'**
- PASS **indicators mentions 'Unhealthy particulate'**

### S08_all_sources_down: Every data source failed
_No data is not good news. Confidence must be low, the report must say 'insufficient data', and it must never claim zero fires or calm winds._

- PASS **confidence** got 0.20, want <= 0.3
- PASS **summary mentions 'Insufficient data'**
- PASS **findings avoids 'Zero active thermal hotspots'**
- PASS **findings avoids 'Wind recorded'**
- PASS **summary avoids 'stable baseline'**
- PASS **data gap 'fire:error' reported** gaps=['air_quality:error', 'fire:error', 'weather:error']
- PASS **data gap 'weather:error' reported** gaps=['air_quality:error', 'fire:error', 'weather:error']
- PASS **data gap 'air_quality:error' reported** gaps=['air_quality:error', 'fire:error', 'weather:error']

### S09_no_air_quality_coverage: Fire downwind, but no air-quality station covers the town
_Missing AQ coverage must be reported as a gap, not as clean air, and the summary must say it is incomplete._

- PASS **downwind flag** got True, want True
- PASS **findings mentions 'No active in-situ'**
- PASS **summary mentions 'incomplete'**
- PASS **summary avoids 'stable baseline'**
- PASS **data gap 'air_quality:no_data' reported** gaps=['air_quality:no_data']

### S10_modeled_air_quality: PM2.5 comes from a model, not a sensor
_Modeled values are weaker evidence: confidence must drop below a fully-observed run and the finding must say the value is modeled._

- PASS **confidence** got 0.90, want <= 0.9
- PASS **findings mentions 'modeled estimate'**
