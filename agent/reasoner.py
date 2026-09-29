"""Deterministic reasoner & optional LLM synthesis for TerraWatch."""

from __future__ import annotations

import os
from typing import Any, Dict, List, Sequence
from data.schemas.models import Evidence


def compute_confidence(evidence_list: Sequence[Evidence]) -> float:
    """Computes a 0.0 to 1.0 confidence score based on evidence quality and coverage."""
    if not evidence_list:
        return 0.0

    total_sources = len(evidence_list)
    ok_sources = sum(1 for ev in evidence_list if ev.status == "ok")
    modeled_count = sum(1 for ev in evidence_list if ev.is_modeled)

    base_score = ok_sources / total_sources

    # Penalize modeled fallback data (e.g. CAMS fallback instead of real sensor stations)
    if modeled_count > 0:
        base_score -= 0.10 * modeled_count

    return round(max(0.2, min(0.98, base_score)), 2)


def generate_synthesis(
    question: str,
    analysis: Dict[str, Any],
    evidence_list: Sequence[Evidence],
) -> Dict[str, Any]:
    """Produces key findings, risk indicators, and an executive summary.

    Prioritizes deterministic, factual synthesis strictly from computed metrics.
    If an LLM API key is present (GROQ_API_KEY), it can refine the narrative while
    anchoring on the exact computed numbers.
    """
    signals = analysis["signals"]
    target = analysis["target"]
    risk_level = analysis["risk_level"]
    risk_score = analysis["risk_score"]
    components = analysis["components"]

    findings: List[str] = []
    indicators: List[str] = []

    # 1. Fire signals
    fire_count = signals.get("fire_count", 0)
    nearest_km = signals.get("nearest_fire_km")
    if fire_count > 0 and nearest_km is not None:
        findings.append(
            f"Detected {fire_count} active thermal hotspot(s) within the scanning radius, closest at {nearest_km} km."
        )
        if nearest_km <= 75.0:
            indicators.append(f"Elevated fire proximity risk: hotspot located {nearest_km} km from {target['name']}.")
    else:
        findings.append(f"Zero active thermal hotspots detected within target radius around {target['name']}.")

    # 2. Wind & Plume Alignment
    wind_spd = signals.get("wind_speed_kmh", 0.0)
    wind_dir = signals.get("wind_direction_deg", 0.0)
    downwind = signals.get("is_downwind_of_fire", False)

    findings.append(
        f"Wind recorded at {wind_spd} km/h blowing from {wind_dir}°."
    )
    if downwind and fire_count > 0:
        indicators.append(
            f"Adverse smoke transport: {target['name']} is situated directly downwind of active fires."
        )
    elif fire_count > 0:
        findings.append(f"{target['name']} is currently upwind or crosswind relative to active fires.")

    # 3. Air Quality
    pm25 = signals.get("pm25_ug_m3")
    pm25_anomaly = signals.get("pm25_anomaly_ratio", 0.0)
    if pm25 is not None:
        findings.append(f"Ambient PM2.5 measured at {pm25} µg/m³ (anomaly ratio: {pm25_anomaly:.2f}).")
        if pm25 > 35.0:
            indicators.append(f"Unhealthy particulate matter concentration: PM2.5 at {pm25} µg/m³ exceeds safe thresholds.")
    else:
        findings.append("No active in-situ air quality sensor station reporting in target perimeter.")

    # 4. Executive Summary
    summary = (
        f"Environmental risk assessment for {target['name']} is rated {risk_level} (score: {risk_score:.2f}). "
    )
    if indicators:
        summary += "Primary concern(s): " + " ".join(indicators)
    else:
        summary += "Available environmental signals indicate stable baseline conditions."

    # Optional Groq LLM refinement if key is available
    groq_key = os.getenv("GROQ_API_KEY")
    if groq_key:
        try:
            from langchain_groq import ChatGroq
            from langchain_core.prompts import PromptTemplate

            prompt = PromptTemplate.from_template(
                "You are TerraWatch's Environmental Crisis Intelligence Agent.\n"
                "Question: {question}\n"
                "Target: {target}\n"
                "Risk Level: {risk_level} ({risk_score})\n"
                "Deterministic Findings: {findings}\n"
                "Risk Indicators: {indicators}\n\n"
                "Write a concise, professional 2-sentence executive summary strictly using the evidence provided above. "
                "Do NOT invent numbers or hazards."
            )
            llm = ChatGroq(model="openai/gpt-oss-20b", temperature=0, groq_api_key=groq_key)
            chain = prompt | llm
            res = chain.invoke({
                "question": question,
                "target": target["name"],
                "risk_level": risk_level,
                "risk_score": f"{risk_score:.2f}",
                "findings": "; ".join(findings),
                "indicators": "; ".join(indicators) if indicators else "None",
            })
            if res.content and len(res.content.strip()) > 20:
                summary = res.content.strip()
        except Exception:
            pass  # Fallback to deterministic summary if LLM call fails

    return {
        "key_findings": findings,
        "risk_indicators": indicators,
        "executive_summary": summary,
    }
