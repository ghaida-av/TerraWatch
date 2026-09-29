# AGENT.md — TerraWatch Autonomous Agent Manifest & Working Log

## 1. Project Overview & Mission

**TerraWatch** is an environmental crisis intelligence agent built for the **Connected Data Agents** track.
The system connects fragmented environmental and geographic data sources, investigates a location/crisis question, deterministically correlates signals across sources, and produces an evidence-backed, calibrated risk assessment.

### Core Workflow
```text
User Question & Location
         ↓
Agent Planner (extract intent & required sources)
         ↓
Data Layer (Open-Meteo, OpenAQ, NASA FIRMS, USGS, OSM/Geoapify)
         ↓
Normalized Evidence Envelopes (pydantic models with UTC, units, content hash IDs)
         ↓
Deterministic Analysis Engine (Spatial, Wind Vectors, Temporal Correlation, Risk Math)
         ↓
Evidence Graph (Nodes & Directed Relationships)
         ↓
LLM Reasoner (Reasons strictly over structured evidence & metrics — zero hallucinated math)
         ↓
Final Structured Investigation Report
```

### Critical Architecture Rule (Non-Negotiable)
> **Keep deterministic analysis outside the LLM.**
> Raw API data must pass through Python calculation engines first (`fire_distance_km`, `wind_alignment`, `pm25_anomaly`, `temporal_correlation`).
> The LLM receives **structured metrics**, not unparsed data dumps. The LLM explains and summarizes; Python calculates.

---

## 2. Team Architecture & Ownership Matrix

| Role | Domain | Core Ownership | Deliverable |
|---|---|---|---|
| **P1** | 🧠 Agent Lead | Intent routing, investigation planner, reasoning loop, structured final report | `agent/` package (`investigate(location, question)`) |
| **P2** | 🔌 Data Engineer | 5 API connectors (Open-Meteo, OpenAQ, FIRMS, USGS, OSM), normalization, cache, mocks | `data/` package (`collect_evidence()`, `Evidence`) |
| **P3** | 🗺️ Geo / Analysis | Haversine, bearing, wind alignment, downwind check, temporal delta, risk scoring, evidence graph | `geo_analysis/` package (`analyze_evidence()`) |
| **P4** | ⚙️ Backend Engineer | FastAPI, REST endpoints (`POST /investigations`), background jobs, persistence | `apps/api/` |
| **P5** | 🎨 Frontend Engineer | Investigation console, map, live streaming logs, risk badges, graph visualization | `apps/web/` |
| **P6** | 🧪 Product / QA / AI | 10 evaluation scenarios, ground-truth dataset, guardrails, demo reliability | `evals/`, test suite, demo scripts |

---

## 3. Status vs. Execution Plan (Updated)

| Component | Status | Assessment |
|---|---|---|
| **P1: Agent** | 🟢 Complete (Vertical Slice) | Fully extracted from notebook to `agent/` package (`investigate()`, models, CLI with terminal formatting and `--json` export). |
| **P2: Data Layer** | 🟢 Complete (95%) | Production-ready: 5 adapters, cache with stale fallback, mock/demo/live modes, typed schemas. |
| **P3: Geo/Analysis** | 🟢 Complete (95%) | Spatial, wind vectors, temporal delta, risk scoring, evidence graph, and `analyze_evidence` pipeline bridge now fully operational. |
| **P4: Backend** | 🔴 0% | Next up: minimal FastAPI endpoint (`POST /investigations`) wrapping `agent.investigate`. |
| **P5: Frontend** | 🔴 0% | Next up: Web investigation UI with map and evidence graph. |
| **P6: Product / QA** | 🟡 50% | 55 unit/integration tests passing (0.20s), mock scenario and live checks available. |

---

## 4. Instructions for All AI Agents Touching This Codebase

Any agent (human or AI) modifying this repository **MUST** follow these operating rules:

1. **Always Update This File (`AGENT.md`)**:
   - Register any changes, bug fixes, refactors, or new files in the **Change & Bug Log** below.
   - Clearly state what was changed, the rationale, and test status.
2. **Never Run Unnormalized Data into LLMs**:
   - Every metric sent to an LLM must originate from `data/` normalized schemas and pass through `geo_analysis/` deterministic math.
3. **Never Install Global Packages**:
   - Always run commands in `.venv`. Use `uv` for package management.
   - Run commands from repository root only.
4. **Git Hygiene**:
   - Short imperative commits: `type: short description` (max 50 chars).
   - Never commit zip files, colab notebook exports with upload scripts, or `.DS_Store`.
   - Never push to GitHub without explicit user instruction.
5. **Preserve Determinism**:
   - All tests must pass offline (`TERRAWATCH_MODE=mock` or unit tests). Do not rely on external network calls in CI/test suites.

---

## 5. How to Run Investigations

### Local Test Suite
```bash
.venv/bin/pytest
```

### Run an Agent Investigation (Terminal Report)
```bash
# Offline / Mock Mode (instant, no keys needed)
TERRAWATCH_MODE=mock .venv/bin/python -m agent "Cairo"

# Real Live Mode (with API keys)
export OPENAQ_API_KEY=... FIRMS_MAP_KEY=... GEOAPIFY_API_KEY=...
.venv/bin/python -m agent "Cairo" --question "Is smoke from recent fires reaching the city?"
```

### Run an Agent Investigation (Piped JSON Mode)
```bash
TERRAWATCH_MODE=mock .venv/bin/python -m agent "Cairo" --json | jq .
```

---

## 6. Agent Progress & Change Log

### Entry 1 — 2026-09-29 | Initial Assessment & Groundwork
- **Agent**: Antigravity Assistant
- **Status**: Audit completed. 51 unit tests confirmed passing in local virtualenv (`.venv`).
- **Issues Identified**:
  1. Root file ownership previously set to root, fixed by user to `ahmedm-t`.
  2. Binary artifacts committed: `TerraWatch-main (1).zip`, `TerraWatch-main (2).zip`.
  3. Dirty Colab upload in root: `spatial_and_wind.py`.
  4. Double-execution bug in `geo_analysis/show_geo_numbers.py` (lines 215–333).
  5. Missing bridge connecting `data.Evidence` to `geo_analysis` correlation engine.
  6. Agent code confined to Colab notebook `TerraWatch_AI_System.ipynb`.

### Entry 2 — 2026-09-29 | 3-Step Execution: Cleanup, Pipeline Bridge & Agent Package
- **Agent**: Antigravity Assistant
- **Status**: All 3 steps executed and tested. 55 unit tests passing.
- **Actions Taken**:
  1. **Step 1 (Repo Cleanup)**:
     - Deleted binary zips `TerraWatch-main (1).zip` and `TerraWatch-main (2).zip`.
     - Deleted raw Colab script `spatial_and_wind.py` in the root.
     - Removed duplicate lines 215–333 from `geo_analysis/show_geo_numbers.py` preventing double execution.
  2. **Step 2 (Data → GeoAnalysis Pipeline Bridge)**:
     - Implemented `geo_analysis/pipeline.py` with `analyze_evidence(evidence_list, target_name, target_lat, target_lon)`.
     - Bridges `data.schemas.models.Evidence` objects directly into spatial, wind vector, air quality anomaly, temporal correlation, and evidence graph nodes.
     - Updated `geo_analysis/__init__.py` to export the public API.
     - Added comprehensive unit tests in `tests/test_pipeline.py`.
  3. **Step 3 (Agent Package & CLI Runner)**:
     - Created `agent/models.py` with `InvestigationReport`, `InvestigationLocation`, `RiskComponents`.
     - Created `agent/reasoner.py` for deterministic metric grounding and optional Groq LLM executive synthesis.
     - Created `agent/investigator.py` implementing `investigate(location, question, sources)`.
     - Created `agent/__main__.py` with full terminal dashboard and clean `--json` export.
     - Added unit tests in `tests/test_agent.py`.
- **Test Status**:
  - `55 passed in 0.20s` (across `test_agent`, `test_pipeline`, `test_reliability`, `test_risk`, `test_live_parsing`, `test_mock_scenario`, `test_show_geo_numbers`, `test_spatial`, `test_temporal`, `test_wind`).

---

## 7. Next Up (Roadmap)

1. **Person 4 (Backend)**: Build minimal FastAPI endpoint in `apps/api/` exposing `POST /investigations` calling `agent.investigate()`.
2. **Person 5 (Frontend)**: Build web console in `apps/web/` with Leaflet map, risk badge cards, and evidence graph viewer.
3. **Person 6 (QA & Evals)**: Build automated evaluation suite across 10 controlled scenarios.
