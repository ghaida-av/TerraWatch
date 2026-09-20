""" JSON Schemas of the normalized model : backend  and frontend  can
generate types:   python -m scripts.export_schemas   ->  data/schemas/json/*.json"""
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from data.schemas import models as m  # noqa: E402

OUT = Path(__file__).resolve().parents[1] / "data" / "schemas" / "json"
OUT.mkdir(parents=True, exist_ok=True)
for name in ("Evidence", "WeatherMeasurements", "AirQualityMeasurements", "FireMeasurements",
             "EarthquakeMeasurements", "GeoMeasurements", "GeocodeMeasurements"):
    (OUT / f"{name}.json").write_text(json.dumps(getattr(m, name).model_json_schema(), indent=2))
    print("wrote", OUT / f"{name}.json")
