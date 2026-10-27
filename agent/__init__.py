"""TerraWatch Agent Package."""

from agent.llm import load_env_file  # noqa: E402  (loads project .env before provider settings resolve)
load_env_file()

from agent.investigator import investigate
from agent.models import InvestigationReport, InvestigationLocation, RiskComponents

__all__ = [
    "investigate",
    "InvestigationReport",
    "InvestigationLocation",
    "RiskComponents",
]
