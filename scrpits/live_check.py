""" REAL APIs  and report what came back. 

    export OPENAQ_API_KEY=... FIRMS_MAP_KEY=... GEOAPIFY_API_KEY=...
    python -m scripts.live_check                    # check Cairo, no files written
    python -m scripts.live_check --record           # also record demo fixtures for Cairo, LA and Tokyo
    python -m scripts.live_check --place tokyo


"""
from __future__ import annotations

import argparse
import os
import sys
import time
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

PLACES = {  # name: (lat, lon, city, country)   — chosen to match the plan's scenarios
    "cairo": (30.0444, 31.2357, "Cairo", "Egypt"),
    "los_angeles": (34.0522, -118.2437, "Los Angeles", "United States"),   # California wildfire scenario
    "tokyo": (35.6762, 139.6503, "Tokyo", "Japan"),                        # earthquake scenario
}


def headline(ev) -> str:
    m = ev.measurements
    if ev.status == "error":
        return f"{ev.error.type}: {ev.error.message[:110]}"
    if ev.kind == "weather" and m.get("current"):
        c = m["current"]
        return f"{c['temperature_c']}°C wind {c['wind_speed_kmh']} km/h from {c['wind_direction_deg']}°  ({m['hourly_count']} hourly rows)"
    if ev.kind == "air_quality":
        st = (m.get("station") or {}).get("name")
        return f"PM2.5={m.get('pm25')} PM10={m.get('pm10')} station={st!r} modeled={ev.is_modeled} history={len(ev.observations)}"
    if ev.kind == "fire":
        return f"{m['hotspot_count']} hotspots within {m['radius_km']:.0f} km, nearest={m['nearest_km']} km, product={m['product']}"
    if ev.kind == "earthquake":
        return f"{m['event_count']} events (M{m['min_magnitude']}+), max M{m['max_magnitude']}, nearest={m['nearest_km']} km"
    if ev.kind == "geo":
        return f"{m['feature_count']} features, by_category={m['by_category']}"
    if ev.kind == "geocode":
        return f"{m['matched_name']} tz={m['tz_name']} -> {ev.location.lat:.4f},{ev.location.lon:.4f}"
    return ev.status


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--record", action="store_true", help="save successful responses as DEMO-mode fixtures")
    ap.add_argument("--place", choices=list(PLACES), help="only this place (default: cairo, or all with --record)")
    args = ap.parse_args()

    os.environ["TERRAWATCH_MODE"] = "live"
    if args.record:
        os.environ["TERRAWATCH_RECORD_FIXTURES"] = "1"

    from data import ADAPTERS, geocode
    from data.core.cache import get_cache

    get_cache().clear()  # make sure we really hit the network (and record what we hit)
    names = [args.place] if args.place else (list(PLACES) if args.record else ["cairo"])
    failures = 0
    for name in names:
        lat, lon, city, country = PLACES[name]
        print(f"\n=== {name} ({lat}, {lon}) ===")
        results = [geocode(city, country)] + [
            ADAPTERS[k].fetch(lat, lon, **({"categories": "critical_infrastructure"} if k == "geo" else {}))
            for k in ("weather", "air_quality", "fire", "earthquake", "geo")
        ]
        for ev in results:
            t0 = time.time()
            flag = {"ok": "OK   ", "no_data": "EMPTY", "error": "FAIL "}[ev.status]
            failures += ev.status == "error"
            print(f"[{flag}] {ev.kind:<12} {ev.source:<24} {ev.data_mode:<11} {headline(ev)}")
            for w in ev.warnings:
                print(f"         ! {w}")
    print(f"\n{failures} source(s) failed.")
    if args.record:
        from data.config import fixtures_dir
        print(f"Fixtures written under {fixtures_dir()} — commit them so DEMO mode works on every machine.")
    return 1 if failures else 0


if __name__ == "__main__":
    raise SystemExit(main())
