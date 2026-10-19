"""Output guardrails for LLM-written summaries.

TerraWatch's rule is "Python calculates, the LLM explains". A prompt can ask the model to follow that rule,
but it cannot enforce it, so every LLM summary is *verified* here before it can reach a report. A summary is
rejected (and the deterministic summary is used instead) when it:

  1. contains a number that is not traceable to the computed metrics / findings,
  2. states a risk level that contradicts the computed one,
  3. talks about a hazard for which there is no evidence at all (e.g. earthquakes, floods),
  4. is empty, or absurdly long.
"""
from __future__ import annotations

import re
from dataclasses import dataclass, field
from typing import Any, Dict, Iterable, List, Mapping, Sequence, Set

LEVELS = ("LOW", "MODERATE", "HIGH", "CRITICAL")
MAX_SUMMARY_CHARS = 1200

# Hazards the LLM may only discuss if matching evidence exists. keyword -> evidence kind that licenses it.
_HAZARD_TERMS: Dict[str, str] = {
    "earthquake": "earthquake", "seismic": "earthquake", "tremor": "earthquake", "tsunami": "earthquake",
    "flood": "", "radiation": "", "nuclear": "", "chemical": "", "volcan": "", "hurricane": "", "cyclone": "",
    "tornado": "", "landslide": "", "drought": "",
}

# "PM2.5", "PM10", "NO2" ... contain digits that are names, not measurements.
_POLLUTANT_NAMES = re.compile(r"\b(?:PM\s?2\.5|PM\s?10|NO2|O3|SO2|CO2)\b", re.IGNORECASE)
_NUMBER = re.compile(r"(?<![\w.])-?\d+(?:,\d{3})*(?:\.\d+)?")
_LEVEL_CLAIM = re.compile(
    r"(?:rated|rating(?:\s+of)?|risk\s+level(?:\s+is)?|level\s+of|risk\s+is|assessed\s+as|classified\s+as)\s*:?\s*"
    r"(LOW|MODERATE|HIGH|CRITICAL)\b|\b(LOW|MODERATE|HIGH|CRITICAL)\s+(?:risk|threat)\b",
    re.IGNORECASE,
)


@dataclass
class GuardrailResult:
    ok: bool
    reasons: List[str] = field(default_factory=list)


def extract_numbers(text: str) -> List[float]:
    cleaned = _POLLUTANT_NAMES.sub(" ", text or "")
    out: List[float] = []
    for m in _NUMBER.findall(cleaned):
        try:
            out.append(float(m.replace(",", "")))
        except ValueError:
            continue
    return out


def _decimals(raw: str) -> int:
    return len(raw.split(".")[1]) if "." in raw else 0


def build_allowed_numbers(analysis: Mapping[str, Any], findings: Iterable[str], indicators: Iterable[str]) -> Set[float]:
    """Every number the summary is allowed to quote: those in the findings plus all computed metrics."""
    allowed: Set[float] = set()
    for text in list(findings) + list(indicators):
        allowed.update(extract_numbers(text))

    def walk(obj: Any) -> None:
        if isinstance(obj, bool):
            return
        if isinstance(obj, (int, float)):
            allowed.add(float(obj))
        elif isinstance(obj, Mapping):
            for v in obj.values():
                walk(v)

    for key in ("risk_score", "components", "signals"):
        walk(analysis.get(key))
    return allowed


def _is_grounded(raw: str, allowed: Set[float]) -> bool:
    value = float(raw.replace(",", ""))
    d = _decimals(raw)
    for a in allowed:
        if round(a, d) == round(value, d):              # same number at the precision the summary used
            return True
        if round(a * 100, d) == round(value, d):        # 0.62 quoted as "62%"
            return True
        if d == 0 and abs(a - value) < 0.5 + 1e-9:      # 58.4 quoted as "58"
            return True
    return False


def check_summary(
    summary: str,
    *,
    allowed_numbers: Set[float],
    risk_level: str,
    evidence_kinds: Sequence[str],
) -> GuardrailResult:
    reasons: List[str] = []
    text = (summary or "").strip()

    if len(text) < 20:
        return GuardrailResult(False, ["summary is empty or too short"])
    if len(text) > MAX_SUMMARY_CHARS:
        reasons.append(f"summary is longer than {MAX_SUMMARY_CHARS} characters")

    # 1. numbers must be traceable
    cleaned = _POLLUTANT_NAMES.sub(" ", text)
    ungrounded = sorted({m for m in _NUMBER.findall(cleaned) if not _is_grounded(m, allowed_numbers)})
    if ungrounded:
        reasons.append("numbers not found in the computed evidence: " + ", ".join(ungrounded))

    # 2. stated risk level must match
    for m in _LEVEL_CLAIM.finditer(text):
        claimed = (m.group(1) or m.group(2)).upper()
        if claimed != risk_level.upper():
            reasons.append(f"states risk level {claimed} but the computed level is {risk_level.upper()}")
            break

    # 3. no invented hazards
    kinds = set(evidence_kinds)
    lowered = text.lower()
    for term, licensed_by in _HAZARD_TERMS.items():
        if term in lowered and not (licensed_by and licensed_by in kinds):
            reasons.append(f"mentions '{term}' but there is no evidence for it")

    return GuardrailResult(not reasons, reasons)
