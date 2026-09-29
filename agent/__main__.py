"""CLI entrypoint for TerraWatch investigation agent."""

from __future__ import annotations

import argparse
import json
import sys

from agent.investigator import investigate


def main() -> int:
    parser = argparse.ArgumentParser(
        description="TerraWatch — Autonomous Environmental Crisis Investigation Agent"
    )
    parser.add_argument(
        "location",
        nargs="?",
        default="Cairo",
        help="Target city or location to investigate (default: Cairo)",
    )
    parser.add_argument(
        "--question",
        "-q",
        default="What environmental risks exist?",
        help="Investigation inquiry / question",
    )
    parser.add_argument(
        "--country",
        "-c",
        default="",
        help="Country hint to disambiguate location",
    )
    parser.add_argument(
        "--sources",
        "-s",
        nargs="+",
        default=["weather", "air_quality", "fire"],
        help="Data sources to query (default: weather air_quality fire)",
    )
    parser.add_argument(
        "--json",
        action="store_true",
        help="Output raw JSON InvestigationReport",
    )

    args = parser.parse_args()

    log_file = sys.stderr if args.json else sys.stdout
    print(f"\n🔍 [TerraWatch] Initiating investigation for: {args.location}", file=log_file)
    print(f"❓ Question: {args.question}", file=log_file)
    print(f"📡 Querying Sources: {', '.join(args.sources)}...\n", file=log_file)

    report = investigate(
        location=args.location,
        question=args.question,
        sources=args.sources,
        country_hint=args.country,
    )

    if args.json:
        print(report.model_dump_json(indent=2))
        return 0

    badge_map = {
        "CRITICAL": "\033[91m🔴 CRITICAL\033[0m",
        "HIGH": "\033[91m🟠 HIGH\033[0m",
        "MODERATE": "\033[93m🟡 MODERATE\033[0m",
        "LOW": "\033[92m🟢 LOW\033[0m",
    }
    badge = badge_map.get(report.risk_level, report.risk_level)

    print("=" * 65)
    print(f"   TERRAWATCH CRISIS INTELLIGENCE REPORT")
    print(f"   ID: {report.investigation_id} | Confidence: {int(report.confidence * 100)}%")
    print("=" * 65)
    print(f"📍 Target: {report.target.name} ({report.target.lat:.4f}, {report.target.lon:.4f})")
    print(f"⚠️  Overall Risk Assessment: {badge} (Score: {report.risk_score:.2f})")
    print("-" * 65)
    print("📊 Risk Component Breakdown:")
    print(f"   - Fire Proximity:        {report.components.proximity:.2f}")
    print(f"   - Wind Alignment:        {report.components.wind_alignment:.2f}")
    print(f"   - Air Quality Anomaly:   {report.components.air_quality_anomaly:.2f}")
    print(f"   - Temporal Correlation:  {report.components.temporal_correlation:.2f}")
    print("-" * 65)
    print("🔎 Primary Evidence Signals:")
    for k, v in report.signals.items():
        print(f"   • {k}: {v}")
    print("-" * 65)
    print("📌 Key Factual Findings:")
    for f in report.key_findings:
        print(f"   ✓ {f}")
    if report.risk_indicators:
        print("\n🚨 Risk Indicators:")
        for ind in report.risk_indicators:
            print(f"   ⚠️  {ind}")
    print("-" * 65)
    print(f"📝 Executive Summary:\n   {report.executive_summary}")
    print("-" * 65)
    print(f"🔗 Citations: {len(report.evidence_citations)} source envelopes")
    print(f"🕸️  Evidence Graph: {len(report.evidence_graph['nodes'])} nodes, {len(report.evidence_graph['relationships'])} edges")
    print("=" * 65 + "\n")
    return 0


if __name__ == "__main__":
    sys.exit(main())
