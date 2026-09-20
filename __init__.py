"""TerraWatch data layer (Person 2). Public surface: see README."""
from data.registry import ADAPTERS, ALL_SOURCES, MVP_SOURCES, collect_evidence, geocode  # noqa: F401
from data.schemas.models import Evidence  # noqa: F401
from data.store import get_evidence  # noqa: F401
