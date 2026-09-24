# TerraWatch import reference

This file lists the import paths that are valid in this repository.
Use these exact imports; do not invent alternate package names.

## 1) Top-level data API

```python
from data import collect_evidence, geocode, get_evidence
from data.registry import ADAPTERS, ALL_SOURCES, MVP_SOURCES, collect_evidence, geocode
from data.store import get_evidence
from data.schemas.models import Evidence
```

These are the main entry points for the app and are the safest imports to use from outside the package.

## 2) Adapter classes

```python
from data.adapters import (
    AirQualityAdapter,
    EarthquakeAdapter,
    FireAdapter,
    GeoAdapter,
    GeocodeAdapter,
    WeatherAdapter,
)
```

## 3) Adapter submodules

These imports are also valid and match the actual package layout:

```python
from data.adapters.base import BaseAdapter, Fetched
from data.adapters.firms import FireAdapter
from data.adapters.openaq import AirQualityAdapter
from data.adapters.openmeteo import WeatherAdapter
from data.adapters.osm import GeoAdapter, GeocodeAdapter, PRESETS
from data.adapters.usgs import EarthquakeAdapter
```

## 4) Registry and tool wrappers

```python
from data.registry import ADAPTERS, ALL_SOURCES, MVP_SOURCES
from data.tools import TOOLS, TOOLS_BY_NAME
```

Tool usage examples:

```python
from data.tools import geocode, geo_adapter, weather_adapter, air_quality_adapter, fire_adapter, earthquake_adapter
```

## 5) LangChain tool names used by the notebook / planner

These are the exact tool names exported by `data.tools`:

```python
from data.tools import (
    geocode,
    geo_adapter,
    weather_adapter,
    air_quality_adapter,
    fire_adapter,
    earthquake_adapter,
)
```

They are intentionally designed to match the notebook signatures and return compact LLM-friendly payloads.

## 6) Geo helpers used by the analysis layer

For analysis and geospatial logic, use the project helpers from `data.core.geo`:

```python
from data.core.geo import haversine_km, bearing_deg, destination_point, bbox_from_radius
```

## 7) Example of a working adapter flow

```python
from data import collect_evidence

results = collect_evidence(
    30.0444,
    31.2357,
    sources=["weather", "air_quality", "fire"],
    params={"fire": {"radius_km": 300}},
)

for item in results:
    print(item.kind, item.status, item.evidence_id)
```

## 8) Correct import patterns for each source

### Fire

```python
from data.adapters.firms import FireAdapter
```

### Air quality

```python
from data.adapters.openaq import AirQualityAdapter
```

### Weather

```python
from data.adapters.openmeteo import WeatherAdapter
```

### Geo / places / geocoding

```python
from data.adapters.osm import GeoAdapter, GeocodeAdapter
```

### Earthquake

```python
from data.adapters.usgs import EarthquakeAdapter
```

## 9) Common mistakes to avoid

Do not use these invalid or non-canonical paths:

```python
from data.adapters.firms.adapter import FireAdapter  # valid, but not the preferred package import
# preferred: from data.adapters.firms import FireAdapter

from data.adapters import geo_adapter  # this name does not exist in the package namespace
# use: from data.tools import geo_adapter

import data.adapters.firms  # okay for the package, but not the usual way to instantiate the adapter class
# use: from data.adapters.firms import FireAdapter

from data import tools  # not the same as the tool wrappers; use from data.tools import ...
```

## 10) Recommended rule for Person 3A

If you are working on geographic analysis, prefer:

```python
from data.core.geo import haversine_km, bearing_deg
```

If you are working on adapter integration or tool-level API usage, prefer:

```python
from data.tools import TOOLS, TOOLS_BY_NAME
```

If you are working on the backend data layer, prefer:

```python
from data import collect_evidence, geocode, get_evidence
```

This keeps the import paths consistent with the actual package layout in the repository.
