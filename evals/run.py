"""Runs every scenario through the real analysis + reasoner code and checks the expectations."""
from __future__ import annotations

import json
from dataclasses import dataclass, field
from typing import Any, Dict, List, Tuple

from agent.reasoner import compute_confidence, generate_synthesis
from evals import builders as b
from evals.scenarios import SCENARIOS, Scenario
from geo_analysis.pipeline import analyze_evidence

Check = Tuple[str, bool, str]


@dataclass
class Outcome:
    scenario: Scenario
    checks: List[Check]
    observed: Dict[str, Any]

    @property
    def passed(self) -> bool:
        return all(ok for _, ok, _ in self.checks)

    @property
    def status(self) -> str:
        if self.scenario.known_issue:
            return "FIXED" if self.passed else "KNOWN"
        return "PASS" if self.passed else "FAIL"


def run_scenario(s: Scenario) -> Outcome:
    evs = s.evidence()
    analysis = analyze_evidence(evs, target_name=b.TARGET["name"], target_lat=b.TARGET["lat"], target_lon=b.TARGET["lon"])
    confidence = compute_confidence(evs)
    syn = generate_synthesis(s.question, analysis, evs, llm=False)  # deterministic: evals never touch a network
    obs = {
        "risk_level": analysis["risk_level"], "risk_score": analysis["risk_score"], "confidence": confidence,
        "downwind": analysis["signals"]["is_downwind_of_fire"], "fire_count": analysis["signals"]["fire_count"],
        "findings": " | ".join(syn["key_findings"]), "indicators": " | ".join(syn["risk_indicators"]),
        "summary": syn["executive_summary"], "gaps": syn["data_gaps"],
    }
    e, checks = s.expect, []

    def add(name: str, ok: bool, detail: str) -> None:
        checks.append((name, bool(ok), detail))

    if "level_in" in e:
        add("risk level", obs["risk_level"] in e["level_in"], f"got {obs['risk_level']} ({obs['risk_score']:.2f}), want {'/'.join(e['level_in'])}")
    if "score_max" in e:
        add("score cap", obs["risk_score"] <= e["score_max"], f"got {obs['risk_score']:.2f}, want <= {e['score_max']}")
    if "downwind" in e:
        add("downwind flag", obs["downwind"] is e["downwind"], f"got {obs['downwind']}, want {e['downwind']}")
    if "fire_count" in e:
        add("fire count", obs["fire_count"] == e["fire_count"], f"got {obs['fire_count']}, want {e['fire_count']}")
    if "confidence_max" in e:
        add("confidence", obs["confidence"] <= e["confidence_max"], f"got {obs['confidence']:.2f}, want <= {e['confidence_max']}")
    for key, field_name in (("findings_contain", "findings"), ("indicators_contain", "indicators"), ("summary_contains", "summary")):
        for needle in e.get(key, []):
            add(f"{field_name} mentions '{needle}'", needle.lower() in obs[field_name].lower(), "")
    for key, field_name in (("findings_absent", "findings"), ("summary_absent", "summary")):
        for needle in e.get(key, []):
            add(f"{field_name} avoids '{needle}'", needle.lower() not in obs[field_name].lower(), "")
    for g in e.get("gaps_contain", []):
        add(f"data gap '{g}' reported", g in obs["gaps"], f"gaps={obs['gaps']}")
    if e.get("gaps_empty"):
        add("no data gaps", not obs["gaps"], f"gaps={obs['gaps']}")
    return Outcome(s, checks, obs)


def run_all() -> List[Outcome]:
    return [run_scenario(s) for s in SCENARIOS]


def format_table(outcomes: List[Outcome]) -> str:
    lines = [f"{'ID':28} {'STATUS':6} {'LEVEL':9} {'SCORE':5}  NOTE", "-" * 100]
    for o in outcomes:
        note = ""
        if o.status in ("FAIL", "KNOWN"):
            note = "; ".join(f"{n}: {d}" for n, ok, d in o.checks if not ok)[:70]
        lines.append(f"{o.scenario.id:28} {o.status:6} {o.observed['risk_level']:9} {o.observed['risk_score']:<5.2f}  {note}")
    counts = {k: sum(1 for o in outcomes if o.status == k) for k in ("PASS", "FAIL", "KNOWN", "FIXED")}
    lines += ["-" * 100, "  ".join(f"{k}={v}" for k, v in counts.items())]
    return "\n".join(lines)


def format_markdown(outcomes: List[Outcome]) -> str:
    out = ["# TerraWatch evaluation report", "",
           "| Scenario | Status | Level | Score | Confidence |", "|---|---|---|---|---|"]
    for o in outcomes:
        out.append(f"| {o.scenario.id} | {o.status} | {o.observed['risk_level']} | {o.observed['risk_score']:.2f} | {o.observed['confidence']:.2f} |")
    out += ["", "## Scenario details", ""]
    for o in outcomes:
        out += [f"### {o.scenario.id}: {o.scenario.title}", f"_{o.scenario.rationale}_", ""]
        for n, ok, d in o.checks:
            out.append(f"- {'PASS' if ok else 'FAIL'} **{n}** {d}".rstrip())
        if o.scenario.known_issue:
            out += ["", f"> **Known issue:** {o.scenario.known_issue}"]
        out.append("")
    return "\n".join(out)


def to_json(outcomes: List[Outcome]) -> str:
    return json.dumps([{"id": o.scenario.id, "status": o.status, "observed": o.observed,
                        "checks": [{"name": n, "ok": ok, "detail": d} for n, ok, d in o.checks]} for o in outcomes], indent=2)
