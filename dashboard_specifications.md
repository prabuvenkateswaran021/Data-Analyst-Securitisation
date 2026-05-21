# Dashboard Specifications — 7 Executive Dashboards

Each dashboard is one Power BI report page. Layout is described as a 12-column × 8-row grid (standard 1280×720 px canvas). Visual properties reference DAX measures from `03_dax/dax_measure_library.dax` and columns from the data model.

**Theme:** Dark navy executive theme. Primary: `#0A2540` (deep navy); Accent: `#06B6D4` (cyan); Risk colours: green `#2E7D32`, amber `#F9A825`, orange `#EF6C00`, red `#C62828`.

**Global slicer panel** (left rail, all pages):
- Reporting Date (date hierarchy from `dim_calendar`)
- Servicer (from `dim_servicer`)
- Region & State (from `dim_geography`, drill hierarchy)
- IFRS 9 Stage (from `fact_loan[IFRS9_Stage]`)
- CIBIL Band (from `dim_borrower[CIBILBand_Curr]`)
- Scenario (from `dim_scenario` — applies only to stress dashboard but visible everywhere)

---

# Dashboard 1 — Executive Overview

**Purpose:** Single-pane C-suite view. Answers: *Is the pool healthy this month?*

## Layout

```
┌──────────────────────────────────────────────────────────────────────────────┐
│ ZENITH ABS — POOL ZAAUTO2024-1                       Pool Factor: 0.58       │
│ Executive Overview          [Reporting Date: Oct-2024 ▼]   🟢 HEALTHY        │
├──────────────────────────────────────────────────────────────────────────────┤
│ KPI ROW (cols 1-12, row 1)                                                   │
│ [Current Bal][30+ DPD %][Default Rate][Recovery %][ECL Coverage][WAC][WAM]   │
├──────────────────────────────────────────────────────────────────────────────┤
│ Pool Balance Trend (line chart)         │ IFRS 9 Stage Mix (donut)           │
│ cols 1-7, rows 2-4                      │ cols 8-12, rows 2-4                │
├──────────────────────────────────────────────────────────────────────────────┤
│ Net Loss & Excess Spread (combo)        │ DPD Bucket Distribution (bar)      │
│ cols 1-7, rows 5-6                      │ cols 8-12, rows 5-6                │
├──────────────────────────────────────────────────────────────────────────────┤
│ Geographic ECL Heatmap (filled map of India)         │ Servicer Performance  │
│ cols 1-8, rows 7-8                                   │ Table cols 9-12       │
└──────────────────────────────────────────────────────────────────────────────┘
```

## Visuals & measures

| # | Visual | Type | Measure(s) / Field(s) |
|---|---|---|---|
| 1.1 | Current Pool Balance | KPI card | `[Current Pool Balance]` formatted ₹0.0 Cr |
| 1.2 | Delinquency Rate | KPI card with arrow vs prior month | `[30+ DPD %]`, comparison vs `CALCULATE([30+ DPD %], DATEADD(dim_calendar[Date],-1,MONTH))` |
| 1.3 | Default Rate | KPI card | `[Default Rate %]` |
| 1.4 | Recovery Rate | KPI card | `[Recovery Rate %]` |
| 1.5 | ECL Coverage | KPI card with target line | `[ECL Coverage %]`, target = 5% |
| 1.6 | WAC | KPI card | `[WAC %]` |
| 1.7 | WAM | KPI card | `[WAM Months]` |
| 1.8 | Pool Balance Trend | Line chart | X = `fact_loss_monthly[ReportingDate]`, Y = `BOP_Balance` & `EOP_Balance` |
| 1.9 | IFRS 9 Stage Mix | Donut chart | Legend = `dim_loan[Stage_Label]`, Value = `[Current Pool Balance]`, colour map: Stage 1 = green, Stage 2 = amber, Stage 3 = red |
| 1.10 | Net Loss & Excess Spread | Combo chart | X = date, columns = `NetLoss_ThisMonth`, line = `ExcessSpread_Monthly` |
| 1.11 | DPD Bucket Distribution | Horizontal bar | Y = `DPD_Bucket` (sorted), X = `[Loan Count]`, conditional colour by `[Heat 30+ DPD Colour]` |
| 1.12 | Geographic ECL | Filled map | Location = `dim_geography[State]`, Bubble size = `[Total ECL]`, Colour = `[Heat Stage Mix Colour]` |
| 1.13 | Servicer Performance | Matrix | Rows = ServicerName; cols = Loan Count, Balance, 30+ DPD %, ECL Coverage % |

## Interactions

- **Drill-through:** Right-click any state → `Geographic Detail` page (filtered by selected state).
- **Cross-filter:** Click on stage mix → all visuals filter to that stage. Click on bucket bar → all filter to that bucket.
- **Tooltips:** Custom tooltip page `Loan_Tooltip` showing top 5 risky loans in selection (RANKX by ECL).

---

# Dashboard 2 — Portfolio Analytics

**Purpose:** Composition, segmentation, and vintage health.

## Layout

```
┌──────────────────────────────────────────────────────────────────────────────┐
│ Portfolio Analytics    [Vintage ▼] [LTV Band ▼] [CIBIL Band ▼]               │
├──────────────────────────────────────────────────────────────────────────────┤
│ Vintage Loss Curves (line by VintageID over MOB)                             │
│ cols 1-12, rows 1-3                                                          │
├──────────────────────────────────────────────────────────────────────────────┤
│ LTV Band Stack       │ CIBIL Band      │ DTI Distribution     │ Income Band  │
│ cols 1-3, rows 4-5   │ cols 4-6 rows4-5│ cols 7-9, rows 4-5   │ cols10-12    │
├──────────────────────────────────────────────────────────────────────────────┤
│ Vehicle Type Mix (treemap)   │ Loan Purpose (bar)   │ Servicer share (pie)   │
│ cols 1-5, rows 6-8           │ cols 6-9, rows 6-8   │ cols 10-12, rows 6-8   │
└──────────────────────────────────────────────────────────────────────────────┘
```

## Visuals

| # | Visual | Type | Measure / Field |
|---|---|---|---|
| 2.1 | Vintage Loss Curves | Line | X = `fact_vintage[MonthsOnBook]`, Y = `[Vintage Cumulative Net Loss %]`, Legend = `VintageID`. Reference line at industry benchmark 2%. |
| 2.2 | LTV Band Stack | Stacked column | X = `fact_loan[LTV_Band]`, Y = `[Current Pool Balance]`, Legend = `IFRS9_Stage` |
| 2.3 | CIBIL Band | Column | X = `dim_borrower[CIBILBand_Curr]`, Y = `[Loan Count]` |
| 2.4 | DTI Distribution | Histogram (Field bins) | `fact_loan[DTI_Ratio]` binned in 0.05 buckets |
| 2.5 | Income Band | Column | X = `dim_borrower[IncomeBand]`, Y = `[Current Pool Balance]` |
| 2.6 | Vehicle Type Mix | Treemap | Category = `dim_vehicle[VehicleType]`, Detail = `VehicleMake`, Size = `[Current Pool Balance]` |
| 2.7 | Loan Purpose | Bar | X = `[Loan Count]`, Y = `LoanPurpose` |
| 2.8 | Servicer Share | Pie | Legend = `ServicerName`, Value = `[Current Pool Balance]` |

---

# Dashboard 3 — Credit Risk

**Purpose:** PD/LGD/EAD, IFRS 9 stage migration, DPD, NPA. The risk officer's daily view.

## Layout

```
┌──────────────────────────────────────────────────────────────────────────────┐
│ Credit Risk Dashboard          [Stage ▼] [Snapshot Date ▼]                   │
├──────────────────────────────────────────────────────────────────────────────┤
│ [Wtd PD%][Wtd LGD%][Total EAD][Total ECL][ECL Cov%][NPA%][Stage 3 Cov%]      │
├──────────────────────────────────────────────────────────────────────────────┤
│ Stage Migration Sankey (S1→S2→S3)    │ PD vs LGD Scatter by loan             │
│ cols 1-6, rows 2-5                   │ cols 7-12, rows 2-5                   │
├──────────────────────────────────────────────────────────────────────────────┤
│ DPD Bucket Risk Heatmap (snapshot × bucket)                                  │
│ cols 1-8, rows 6-8                                                           │
│                                      │ NPA Trend (line)                      │
│                                      │ cols 9-12, rows 6-8                   │
└──────────────────────────────────────────────────────────────────────────────┘
```

## Visuals

| # | Visual | Type | Measure / Field |
|---|---|---|---|
| 3.1 | Weighted PD % | KPI | `[Weighted Avg PD %]` |
| 3.2 | Weighted LGD % | KPI | `[Weighted Avg LGD %]` |
| 3.3 | Total EAD | KPI | `[Total EAD]` |
| 3.4 | Total ECL | KPI | `[Total ECL]` |
| 3.5 | ECL Coverage % | KPI gauge | `[ECL Coverage %]` |
| 3.6 | NPA % | KPI gauge | `[NPA %]` (target: <3% for retail; current 5%+ red) |
| 3.7 | Stage 3 Coverage | KPI | `[Stage 3 Coverage %]` |
| 3.8 | Stage Migration Sankey | Custom Sankey | Source: `fact_dpd_snapshot[DPD_Bucket_Prior]`, Target: `DPD_Bucket`, Weight: COUNTROWS |
| 3.9 | PD vs LGD Scatter | Scatter | X = `PD_Estimate`, Y = `LGD_Estimate`, Size = `EAD`, Colour = `IFRS9_Stage`, Detail = `LoanID` |
| 3.10 | DPD Bucket Heatmap | Matrix with cond. formatting | Rows = SnapshotDate, Cols = DPD_Bucket (sorted), Values = COUNTROWS, gradient `[Heat 30+ DPD Colour]` |
| 3.11 | NPA Trend | Line | X = SnapshotDate, Y = `[NPA %]` |

## Drill-through

Right-click any loan in scatter → page `Loan_Detail` with full borrower, payment history, DPD timeline.

---

# Dashboard 4 — Stress Testing

**Purpose:** Scenario-driven impact analysis. *What happens to ECL and the tranches under each scenario?*

## Layout

```
┌──────────────────────────────────────────────────────────────────────────────┐
│ Stress Testing & Scenario Analysis                                           │
│ Scenario: [BASE / MILD / MODERATE / SEVERE / CRISIS]  ◀ button slicer        │
├──────────────────────────────────────────────────────────────────────────────┤
│ Scenario Card: Description + PD Mult + LGD Mult + Unemp Shock + Rate Shock   │
│ cols 1-12, row 1                                                             │
├──────────────────────────────────────────────────────────────────────────────┤
│ [Baseline ECL][Stressed ECL][ECL Δ][ECL Δ%][Stressed PD][Stressed LGD]       │
├──────────────────────────────────────────────────────────────────────────────┤
│ Scenario Comparison Bar  │  Stressed ECL by Stage (stacked col)              │
│ cols 1-6, rows 3-5       │  cols 7-12, rows 3-5                              │
├──────────────────────────────────────────────────────────────────────────────┤
│ Tranche Loss Allocation Under Stress (100% stacked bar by scenario)          │
│ cols 1-7, rows 6-8                                                           │
│                                  │ Sensitivity Table: PD Mult × LGD Mult     │
│                                  │ cols 8-12, rows 6-8                       │
└──────────────────────────────────────────────────────────────────────────────┘
```

## Visuals

| # | Visual | Type | Measure / Field |
|---|---|---|---|
| 4.1 | Scenario Button Slicer | Tiles slicer | `dim_scenario[ScenarioName]` |
| 4.2 | Scenario Card | Multi-row card | Selected scenario attributes from `dim_scenario` |
| 4.3 | Baseline ECL | KPI | `[Total ECL]` |
| 4.4 | Stressed ECL | KPI | `[Stressed ECL]` |
| 4.5 | ECL Δ | KPI | `[ECL Increase from Stress]` |
| 4.6 | ECL Δ % | KPI gauge | `[ECL Increase %]` |
| 4.7 | Scenario Comparison | Bar | X = `dim_scenario[ScenarioName]`, Y = stressed ECL totals (cross-scenario regardless of slicer using ALLEXCEPT) |
| 4.8 | Stressed ECL by Stage | Stacked column | X = Stage (1/2/3), Y = `[Stressed ECL by Stage]`, Legend = Scenario |
| 4.9 | Tranche Loss Allocation | 100% stacked bar | X = ScenarioName, Y = Loss, Legend = Tranche (TR-C bottom, TR-B middle, TR-A top) |
| 4.10 | Sensitivity Table | Matrix | Rows = PD multipliers, Cols = LGD multipliers, Value = computed stressed ECL via what-if parameters |

## Special: What-if parameters

Create two **what-if parameters** in Power BI Desktop:
- `PD Multiplier Override` (0.5 to 5.0, step 0.1)
- `LGD Multiplier Override` (0.5 to 2.0, step 0.05)

These override the scenario defaults when the user moves the slider, enabling **ad-hoc stress testing** beyond the 5 pre-built scenarios. Measure:

```dax
[Stressed ECL (What-If)] =
    VAR _pdm  = SELECTEDVALUE ( 'PD Multiplier Override'[Value], [Scenario PD Multiplier] )
    VAR _lgdm = SELECTEDVALUE ( 'LGD Multiplier Override'[Value], [Scenario LGD Multiplier] )
    RETURN
        SUMX (
            fact_loan,
            MIN ( fact_loan[PD_Estimate] * _pdm, 1 ) *
            MIN ( fact_loan[LGD_Estimate] * _lgdm, 1 ) *
            fact_loan[EAD]
        )
```

---

# Dashboard 5 — Waterfall & Tranche

**Purpose:** Cashflow priority of payments and credit enhancement tracking.

## Layout

```
┌──────────────────────────────────────────────────────────────────────────────┐
│ Waterfall & Tranche Analysis                  [Reporting Date ▼]             │
├──────────────────────────────────────────────────────────────────────────────┤
│ [Senior Bal][Mezz Bal][Eq Bal][Total CE %][Senior Paydown%][Cum Losses to A] │
├──────────────────────────────────────────────────────────────────────────────┤
│ Cash Distribution Waterfall (waterfall chart by step, latest month)          │
│ cols 1-12, rows 2-4                                                          │
├──────────────────────────────────────────────────────────────────────────────┤
│ Tranche Paydown Over Time (line, one per tranche)                            │
│ cols 1-7, rows 5-8                                                           │
│                              │ Loss Allocation Stack (col by month, legend=tr│
│                              │ cols 8-12, rows 5-8                           │
└──────────────────────────────────────────────────────────────────────────────┘
```

## Visuals

| # | Visual | Type | Measure / Field |
|---|---|---|---|
| 5.1 | Senior Balance | KPI | Filtered `[Tranche EOP Balance]` for TR-A |
| 5.2 | Mezz Balance | KPI | TR-B |
| 5.3 | Equity Balance | KPI | TR-C |
| 5.4 | Credit Enhancement | KPI gauge | `[Credit Enhancement %]` (target ≥ 20%) |
| 5.5 | Senior Paydown % | KPI | `[Tranche Paydown %]` for TR-A |
| 5.6 | Cum Losses to A | KPI | Filtered `[Cumulative Tranche Loss]` |
| 5.7 | Cash Distribution Waterfall | Native waterfall | Category = `fact_waterfall_distribution[Step]` (sorted by `StepNo`), Y = Amount. Latest month only via `TOPN(1, dim_calendar[Date])` filter. |
| 5.8 | Tranche Paydown | Line | X = ReportingDate, Y = `[Tranche EOP Balance]`, Legend = TrancheName |
| 5.9 | Loss Allocation Stack | Stacked column | X = ReportingDate, Y = LossAllocated, Legend = TrancheName (TR-C bottom) |

---

# Dashboard 6 — Investor Reporting

**Purpose:** Monthly investor pack: pool stats, prepayments, yield, exposure by holder.

## Layout

```
┌──────────────────────────────────────────────────────────────────────────────┐
│ Investor Pack — ZAAUTO2024-1                            [Reporting Date ▼]   │
├──────────────────────────────────────────────────────────────────────────────┤
│ Pool Stats Header (multi-card): Pool Factor / WAC / WAM / WALA / CDR / CPR   │
├──────────────────────────────────────────────────────────────────────────────┤
│ CPR vs CDR History (combo)             │ Collection Efficiency Trend (line)  │
│ cols 1-6, rows 2-4                     │ cols 7-12, rows 2-4                 │
├──────────────────────────────────────────────────────────────────────────────┤
│ Investor Allocation Table              │ Investor Type Mix (donut)           │
│ cols 1-7, rows 5-8                     │ cols 8-12, rows 5-8                 │
└──────────────────────────────────────────────────────────────────────────────┘
```

## Visuals

| # | Visual | Type | Measure / Field |
|---|---|---|---|
| 6.1 | Pool Factor | KPI | `[Pool Factor]` |
| 6.2 | WAC | KPI | `[WAC %]` |
| 6.3 | WAM | KPI | `[WAM Months]` |
| 6.4 | WALA | KPI | `[WALA Months]` |
| 6.5 | CDR Annualised | KPI | `[CDR Annualised %]` |
| 6.6 | CPR Annualised | KPI | `[CPR Annualised %]` |
| 6.7 | CPR vs CDR History | Combo | X = date, lines = `[CPR Annualised %]` and `[CDR Annualised %]` |
| 6.8 | Collection Efficiency | Line + target | Y = `[Collection Efficiency %]`, target line at 100% |
| 6.9 | Investor Allocation | Matrix | Rows = InvestorName, Cols = Tranche, Values = InvestedAmount_INR, Cumulative Interest Received |
| 6.10 | Investor Type Mix | Donut | Legend = InvestorType, Value = InvestedAmount_INR |

---

# Dashboard 7 — Gamified Risk Arena (Concept)

**Purpose:** Decision-simulation environment for credit analysts. Treats portfolio management as a turn-based game where the analyst makes decisions month-by-month and sees the consequences.

## Concept

You start at **Month 0** (cutoff) with the live pool. Each "round" advances one month. Before each round, the analyst makes three decisions:

1. **Collection strategy** — soft / standard / aggressive (affects cure rate, customer churn)
2. **Restructuring policy** — strict / moderate / permissive (affects Stage 2 inflow)
3. **Reserve top-up** — none / 0.5% / 1% of EOP balance (affects yield, ECL coverage)

A macro die roll injects randomness: each month one of {growth, stagflation, mild shock, severe shock} from a weighted distribution. The system computes the impact and shows the resulting portfolio state vs the baseline.

A **scorecard** tracks:
- Investor IRR realised
- Total ECL released or charged
- # NPA breaches (>5% triggers warning, >8% triggers downgrade)
- Cumulative losses to Senior tranche (the lose condition)

## Workflow visualisation

```
┌────────────────────────────────────────────────────────────────────┐
│  CRISIS MANAGEMENT SIMULATOR — Month 7 of 24                       │
│  Score: 78/100      🏆 Achievements: First-Year Survivor           │
├────────────────────────────────────────────────────────────────────┤
│  CURRENT STATE                       │   NEXT MONTH OUTLOOK         │
│  Pool Balance: ₹321 Cr ↓             │   Stochastic shock: STAG-FLAT│
│  Stage 3 %:   3.2%   ↑               │   Confidence: 67%            │
│  ECL Cov %:   4.8%                   │   Expected ECL Δ: +₹4.2 L    │
├────────────────────────────────────────────────────────────────────┤
│  DECISION 1: Collection Strategy                                   │
│  ◯ Soft   ◯ Standard  ● Aggressive                                 │
│  Trade-off: +cure rate −retention (churn risk +12%)                │
│                                                                    │
│  DECISION 2: Restructuring Policy                                  │
│  ● Strict ◯ Moderate  ◯ Permissive                                 │
│  Trade-off: −forbearance abuse −reputation                         │
│                                                                    │
│  DECISION 3: Reserve top-up                                        │
│  ◯ None  ◯ 0.5%  ● 1.0%                                            │
│  Trade-off: −investor yield +rating buffer                         │
│                                                                    │
│  [ COMMIT → ADVANCE MONTH ]                                        │
├────────────────────────────────────────────────────────────────────┤
│  HISTORY (last 6 months) — line chart of score and ECL coverage   │
└────────────────────────────────────────────────────────────────────┘
```

## Implementation in Power BI (concept-stage)

- Build a Power BI **paginated report** or **Power Apps embedded visual** with:
  - Three single-select slicers (the three decisions)
  - One button that triggers a stored procedure (via Power Automate) to advance state in a SQL backend.
  - The backend persists a "GameState" table and writes the next snapshot.
- Visuals re-bind on refresh.
- Alternatively, prototype in a React/HTML app and embed via the Power BI Web Content visual.

## Business value

- **Training:** Analysts learn the interplay between collection policy and IFRS 9 staging.
- **Hiring:** Standardised scenario assessment for credit-risk hires.
- **Model validation:** Repeated runs surface edge cases in stress assumptions.
- **Client demos:** Clearly differentiates the platform from static dashboards.

A proof-of-concept of the visual layer is included as an HTML prototype in `06_prototype/`.

---

# Cross-dashboard interaction patterns

| Pattern | Implementation |
|---|---|
| **Drill-through to loan detail** | All pages → right-click → `Loan_Detail` page, filtered by selected LoanID |
| **Drill-through to state** | Geographic visuals → `Geographic_Detail` page |
| **Bookmarks** | "Healthy view", "Stress view", "Investor view" — pre-built bookmark selectors |
| **Sync slicers** | Reporting Date, Servicer, Region sync across all pages |
| **Tooltips** | Custom tooltip page `Risk_Tooltip` shows top 3 risky loans on hover over any aggregate visual |
| **What-if interactivity** | Stress page only; PD and LGD multipliers control all stressed calculations |

# Accessibility

- All KPI cards display value, target, and arrow direction (do not rely on colour alone).
- Heatmaps use a colour-blind safe sequential scale (viridis/turbo).
- Alt-text on all visuals.
- Keyboard tab order set on slicers.
