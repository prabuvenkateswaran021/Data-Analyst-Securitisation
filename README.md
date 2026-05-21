# MatRisk AI · v1.0

> **M**aturity, **A**sset & **T**ranche **Risk** **A**nalytics **I**ntelligence
>
> A Python platform for analytics over Indian auto-loan asset-backed
> securitisations: IFRS 9 expected credit loss, RBI-aligned stress
> testing, sequential-pay waterfall mechanics, and an investor-grade
> dashboard.

![architecture](reports/figures/architecture.png)

[![tests](https://img.shields.io/badge/tests-113%20passing-brightgreen)]() [![coverage](https://img.shields.io/badge/coverage-95%25-brightgreen)]() [![python](https://img.shields.io/badge/python-3.10%2B-blue)]() [![license](https://img.shields.io/badge/license-Proprietary-orange)]()

---

## Why this project exists

The pilot pool — `ZAAUTO2024-1`, an Indian retail auto-loan PTC issued
in Q4-2023 — is small (₹54.6 cr original, 500 borrowers) but
representative of the analytics challenges in the segment: 1) loan-level
heterogeneity that makes pool-level back-of-envelope ECL unreliable, 2)
multiple seniority tranches whose cash flows depend on a stochastic
default + prepayment process, and 3) regulatory pressure (RBI Master
Direction 2021, IFRS 9, Basel III) to demonstrate forward-looking,
scenario-dependent loss estimates.

MatRisk AI is the analytical kernel that does the heavy lifting for an
investor (or originator-treasury) view of such a pool: it reads the four
primary data feeds, computes the headline metrics that show up in any
trustee report, runs a five-scenario stress sweep, and ships a
JSON payload that powers an HTML dashboard. The same kernel feeds a
star-schema set of CSVs sized for direct Power BI import.

## Quick start

```bash
# 1. Clone
git clone https://github.com/ZethetaIntern/matrisk-ai
cd matrisk-ai

# 2. Run everything in Docker (recommended)
cp .env.example .env
docker compose up --build

# 3. Open the dashboard
open http://localhost:8000/dashboard

# 4. (Optional) Browse MLflow runs
open http://localhost:5000
```

Or run locally:

```bash
python3.11 -m venv .venv && source .venv/bin/activate
pip install -e ".[dev,docs]"
matrisk pipeline run \
    --raw-dir   data/raw \
    --config    configs/default.yaml \
    --dashboard-out dashboard/data_inline.js
```

## What you get

After one `pipeline run`:

```
data/processed/
├── metrics_portfolio.json     ← pool KPIs (pool factor, WAC, WAM, NPA, ECL)
├── stress_results.csv         ← 5 stress scenarios × ECL + uplift
└── waterfall.csv              ← 84 cash-flow line items across 12 months
dashboard/data_inline.js       ← `window.DATA = {...}` for dashboard.html
```

Sample KPI output for the pilot pool:

| Metric | Value |
|---|---|
| Pool factor | 0.582 |
| Current balance | ₹31.78 cr |
| WAC | 10.95% |
| WAM | 45.1 months |
| Weighted LTV | 67.5% |
| Weighted CIBIL | 742 |
| 30+ DPD | 14.1% of pool |
| NPA (90+) | 5.57% |
| IFRS 9 ECL | ₹1.17 cr (coverage 3.58%) |

Sample stress sweep (PD × LGD multipliers, ECL in cr):

| Scenario | PD mult | LGD mult | ECL | Uplift |
|---|---|---|---|---|
| BASE | 1.00 | 1.00 | 1.17 | — |
| MILD | 1.30 | 1.10 | 1.57 | +35% |
| MODERATE | 1.80 | 1.25 | 2.11 | +81% |
| SEVERE | 2.80 | 1.45 | 3.09 | +165% |
| CRISIS | 4.50 | 1.75 | 4.96 | +325% |

The pilot pool's 18.5% senior credit enhancement absorbs all five
scenarios; mezzanine starts taking writedowns above CRISIS.

## Repository layout

```
matrisk-ai/
├── src/matrisk/             ← installable Python package
│   ├── data/                ← loaders, pydantic schemas
│   ├── analytics/           ← portfolio, credit, stress, waterfall
│   ├── reporting/           ← dashboard payload assembly
│   ├── cli/                 ← click-based CLI (entry point: `matrisk`)
│   └── serve/               ← FastAPI service (/health, /kpis, /stress, /dashboard)
├── tests/                   ← pytest suite (113 tests, 95% coverage)
├── configs/default.yaml     ← all policy thresholds, scenarios, tranches
├── data/
│   ├── raw/                 ← 4 source CSVs
│   └── processed/           ← 18 star-schema dim/fact + pipeline outputs
├── dashboard/               ← HTML dashboard + generated data_inline.js
├── docs/                    ← Sphinx documentation (autodoc)
├── powerbi/                 ← star schema + 110+ DAX measures
├── reports/                 ← technical report + architecture diagram
├── scripts/                 ← MLflow sweep, architecture renderer
├── dvc.yaml                 ← reproducible DAG pipeline
├── docker-compose.yml       ← api + mlflow stack
└── pyproject.toml
```

## Pipeline stages

`matrisk pipeline run` chains five steps:

1. **Ingest** — read the four raw CSVs, normalise column names, coerce
   types, auto-detect ratio columns and rescale to percent.
2. **Portfolio** — compute weighted-average pool KPIs (pool factor,
   WAC, WAM, WALA, LTV, DTI, CIBIL, delinquency buckets, NPA, default
   rate, ECL coverage).
3. **Stress** — apply each scenario from `configs/default.yaml`,
   producing a long-form results frame with optional per-tranche loss
   allocation columns.
4. **Waterfall** — simulate the monthly nine-step sequential-pay
   waterfall across the loss history, returning one row per (period,
   step).
5. **Reporting** — assemble the dashboard payload and write it to
   `data_inline.js`.

DVC users can run the same pipeline as a tracked DAG with
`dvc repro`.

## Configuration

Every policy threshold lives in [`configs/default.yaml`](configs/default.yaml):

- IFRS 9 stage triggers (SICR DPD threshold, CIBIL drop, default DPD)
- LGD collar (floor / ceiling) and Stage-3 PD floor
- 5 stress scenarios with PD/LGD multipliers and macro shocks
- Tranche stack (notional, coupon, rating, rank)
- Waterfall mechanics (servicer fee, trustee fee, cash reserve target)

To run with custom thresholds:

```bash
cp configs/default.yaml configs/scenario_X.yaml
# edit ...
matrisk pipeline run --config configs/scenario_X.yaml
```

## Testing

```bash
pytest --cov=matrisk
```

The CI gate is 60% coverage; the suite currently sits at **95%**:

| Module | Coverage |
|---|---|
| `matrisk.data.loaders` | 93% |
| `matrisk.data.schemas` | 100% |
| `matrisk.analytics.portfolio` | 96% |
| `matrisk.analytics.credit` | 98% |
| `matrisk.analytics.stress` | 100% |
| `matrisk.analytics.waterfall` | 89% |
| `matrisk.reporting.dashboard` | 94% |
| **TOTAL** | **95.29%** |

## MLflow tracking

```bash
python scripts/run_stress_sweep.py
mlflow ui --backend-store-uri file:./mlruns
```

This runs each scenario as a separate MLflow run, logging PD/LGD
multipliers as parameters and stressed ECL + per-tranche loss
absorption as metrics.

## Power BI handoff

`powerbi/model/` contains 10 dimension tables and 8 fact tables
ready to import. `powerbi/dax/dax_measure_library.dax` has 110+
calculated measures (`ECL_Total_Cr`, `Pool_Factor`, `Delinquency_30Plus_Pct`,
`Stress_CRISIS_ECL_Cr`, ...). Wire-frame dashboard specs live under
`powerbi/dashboards/`.

## Documentation

Build the Sphinx site:

```bash
sphinx-build -b html docs/source docs/build/html
open docs/build/html/index.html
```

The Sphinx docs include an autodoc'd API reference plus rendered
methodology pages.

## Contributing

This is proprietary work product under the Indian Patents Act, 1970.
The commit history is itself part of the invention record. External
contributions are not currently accepted; please contact Zetheta
Algorithms Pvt. Ltd. directly.

## IP notice

© 2026 Zetheta Algorithms Pvt. Ltd. All rights reserved.

The MatRisk AI codebase, including all algorithmic novelty around the
LGD-collared lifetime ECL, the bottom-up loss allocation model, and the
parametric stress framework, is the exclusive property of Zetheta
Algorithms Pvt. Ltd. See `LICENSE` for the full proprietary terms.

## References

A full literature review with 20+ academic and regulatory references
appears in [`reports/technical_report.md`](reports/technical_report.md).
