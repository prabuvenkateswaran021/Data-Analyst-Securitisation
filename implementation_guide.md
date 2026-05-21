# Implementation Guide
## Building the Power BI Securitisation Risk Analytics Platform from These Deliverables

This guide walks a Power BI developer through assembling a working `.pbix` file from the artifacts in `01_data/` through `04_dashboards/`. Estimated build time: 4–6 hours for a developer familiar with Power BI and DAX.

---

## Prerequisites

- Power BI Desktop, version November 2023 or later (for native Sankey support and What-If parameters)
- Power Query familiarity (M language)
- Working knowledge of star schema modelling
- Optional: Power BI Service workspace for publication
- Optional: Power BI Pro / Premium licence for paginated reports and subscriptions

---

## Phase 1 — Data Loading (45 min)

### 1.1 Open Power BI Desktop, create new file. Save as `ZenithAutoABS_v1.pbix`.

### 1.2 Set up a parameter for the data path

`Home → Transform Data → Manage Parameters → New Parameter`:
- Name: `DataPath`
- Type: Text
- Current Value: `C:\PowerBI\ZenithAutoABS\01_data\` (or your local path)

This parameterisation lets you move the project between machines without rewriting every query.

### 1.3 Load all 18 tables via Power Query M

Open `02_model/power_query_M_scripts.m`. For each of the 18 M-query blocks:

1. `Home → Transform Data → New Source → Blank Query`
2. `Home → Advanced Editor`
3. Paste the M code for that table
4. Rename the query to match the table name (e.g., `fact_loan`)
5. Verify column data types loaded as expected
6. `Close & Apply` only after all 18 queries are pasted

**Order matters for the first load:** load dimensions first (`dim_calendar`, `dim_borrower`, etc.), then facts. This makes relationship inference cleaner.

### 1.4 Verify row counts

After load, check the data pane shows:
- `fact_loan`: 500 rows
- `fact_dpd_snapshot`: 6,000 rows
- `fact_loss_monthly`: 12 rows
- `fact_vintage`: 375 rows
- `fact_tranche_cashflow`: 36 rows
- `fact_waterfall_distribution`: 108 rows
- `fact_stress_results`: 30 rows
- `fact_economic_history`: 384 rows
- `dim_calendar`: 4,383 rows
- All other dimensions: per the data dictionary

---

## Phase 2 — Data Modelling (60 min)

### 2.1 Switch to Model view

`View → Model`

### 2.2 Build relationships per `02_model/star_schema.md`

For each relationship listed in the schema document:
1. Drag from the foreign key on the fact table to the primary key on the dimension table
2. Verify cardinality is `Many-to-One` (fact:dim)
3. Verify cross-filter direction is `Single` (dim → fact)
4. Verify the relationship is `Active` (except where noted)

**Key active relationships:**

| From | To | On |
|---|---|---|
| `fact_loan.LoanID` | `dim_borrower.LoanID` | LoanID |
| `fact_loan.VehicleKey` | `dim_vehicle.VehicleKey` | VehicleKey |
| `fact_loan.GeoKey` | `dim_geography.GeoKey` | GeoKey |
| `fact_loan.ServicerID` | `dim_servicer.ServicerID` | ServicerID |
| `fact_loan.PoolID` | `dim_pool.PoolID` | PoolID |
| `fact_loan.OriginationDateKey` | `dim_calendar.DateKey` | DateKey |
| `fact_dpd_snapshot.LoanID` | `dim_borrower.LoanID` | LoanID (chains through to fact_loan) |
| `fact_dpd_snapshot.SnapshotDateKey` | `dim_calendar.DateKey` | DateKey |
| `fact_loss_monthly.ReportingDateKey` | `dim_calendar.DateKey` | DateKey |
| `fact_vintage.VintageStartDateKey` | `dim_calendar.DateKey` | DateKey |
| `fact_tranche_cashflow.TrancheID` | `dim_tranche.TrancheID` | TrancheID |
| `fact_waterfall_distribution.MonthDateKey` | `dim_calendar.DateKey` | DateKey |
| `fact_stress_results.ScenarioID` | `dim_scenario.ScenarioID` | ScenarioID |
| `fact_economic_history.IndicatorCode` | `dim_economic_indicator.IndicatorCode` | IndicatorCode |
| `dim_investor.TrancheID` | `dim_tranche.TrancheID` | TrancheID |

**Inactive role-playing relationship** (for USERELATIONSHIP measures):

| From | To | Status |
|---|---|---|
| `fact_loan.CutoffDateKey` | `dim_calendar.DateKey` | INACTIVE |

This lets you swap between origination-date analysis (default) and cut-off-date analysis (via USERELATIONSHIP in DAX).

### 2.3 Mark calendar table

Select `dim_calendar` → Right-click → `Mark as date table` → choose `Date` column.

### 2.4 Hide foreign-key columns from report view

For each foreign-key column on every fact table (e.g., `fact_loan.OriginationDateKey`), right-click → `Hide in report view`. This prevents users from accidentally using FKs in visuals.

### 2.5 Configure column properties

- `fact_loan.OutstandingPrincipal`: Format → Currency → ₹ symbol → 2 decimals
- `fact_loan.CIBIL_Current`: Summarize By → Don't Summarize
- `fact_loan.LTV_Current`: Format → Percentage
- All Date columns: Confirm data type is Date (not DateTime)

---

## Phase 3 — DAX Measures (90 min)

### 3.1 Create a measure-only table

`Home → Enter Data → Name "_Measures" → Load`. This empty table serves as a container for all your measures. Hide its single column.

### 3.2 Paste measures from `03_dax/dax_measure_library.dax`

The DAX library is organised into 17 logical sections. For each measure:

1. Select the `_Measures` table
2. `Home → New Measure`
3. Copy the measure code from the .dax file
4. Press Enter to commit

Recommended order:
1. **Section 1 — Calendar helpers** (5 measures): unlocks time intelligence
2. **Section 2 — Portfolio core** (~12 measures): unlocks Executive Overview
3. **Section 3 — Weighted averages** (WAC/WAM/WALA/LTV/DTI/CIBIL/Yield, ~8 measures)
4. **Section 4 — Delinquency** (30+/60+/90+ DPD %, NPA %, ~10 measures)
5. **Section 5 — Default & Loss** (CDR, MDR, Net Loss %, ~8 measures)
6. **Section 6 — Recovery** (Recovery Rate, ~4 measures)
7. **Section 7 — Prepayment** (SMM, CPR, ~5 measures)
8. **Section 8 — IFRS 9** (Stage counts, ECL, ~12 measures)
9. **Section 9 — Stress** (Stressed ECL with multipliers, ~6 measures)
10. **Section 10 — Tranche & Waterfall** (~10 measures)
11. **Section 11 — Investor** (FPI allocation, ~6 measures)
12. **Section 12 — Collection Efficiency** (~4 measures)
13. **Section 13 — Vintage** (Loss @ 12 MOB, 24 MOB, ~5 measures)
14. **Section 14 — Roll-rate** (~5 measures)
15. **Section 15 — Time intelligence** (DATESYTD with Indian FY, ~8 measures)
16. **Section 16 — Ranking** (RANKX, TOPN, ~4 measures)
17. **Section 17 — Risk-adjusted returns & formatting** (RAROC, traffic-light colors, ~8 measures)

### 3.3 Format measures

For each measure, in the modelling tab:
- Currency measures: ₹ symbol, 2 decimals or 0 decimals as appropriate
- Percentage measures: 0.00% format
- Count measures: 0 format, "#,##0" thousands separator

### 3.4 Validate measure integrity

Create a temporary card visual showing:
- `[Loan Count]` → should display 500
- `[Total Current Balance]` → should display ₹317.78 Cr (~31,77,80,000 in ₹ if displayed in basic units)
- `[Weighted Average Coupon]` → should display 10.95%
- `[Total ECL]` → should display ₹1.17 Cr
- `[ECL Calculated]` → should equal `[Total ECL]` within rounding tolerance

If any of these is off, debug before proceeding to dashboards.

---

## Phase 4 — Dashboards (180 min)

For each of the 7 dashboards, open `04_dashboards/dashboard_specifications.md` and follow the spec page. General workflow per dashboard:

### 4.1 Set page properties

- Page name (e.g., "01 — Executive Overview")
- Page size: Custom, 1280×800 (standard) or 1920×1080 (presentation)
- Background: Solid colour #0A2540 (dark navy)
- Format: Page background → Image (optional dashboard-frame image)

### 4.2 Build the layout grid

The specifications use a 12-column × 8-row grid. Add a temporary grid image as a layer to align by (delete before publishing).

### 4.3 Add visuals one by one

For each visual in the spec:
1. Insert the visual type (Card, Line chart, Bar chart, Donut, etc.)
2. Drag in the fields/measures per the spec
3. Format using the colour scheme:
   - Background: transparent or #1A2332 with 20% opacity
   - Text: White (#FFFFFF) headings, light grey (#CBD5E1) labels
   - Accent: Cyan (#06B6D4) for highlights
   - Risk colours: Green #10B981 / Amber #F59E0B / Orange #FB923C / Red #DC2626
4. Apply conditional formatting on KPI cards using the traffic-light measures
5. Position per the spec layout

### 4.4 Slicers

Add the common slicers (Servicer, Region, Vintage, Date Range) in the spec to each relevant page. Sync these slicers across pages: `View → Sync slicers`.

### 4.5 Drill-throughs

Per spec, create a hidden "Loan Detail" page with `LoanID` as a drill-through field. Right-click any KPI/visual → Drillthrough → Loan Detail.

### 4.6 Cross-filtering

Verify that clicking on a visual filters other visuals on the page appropriately. Some visuals (like the loan-grain detail table) should be excluded from cross-filter via `Format → Edit interactions`.

### 4.7 Tooltips

For each visual, configure a custom tooltip page showing the key context measures. Create a hidden "Tooltip — Loan" page sized 400×320 with key fields, set it as the tooltip target for visuals showing loan-grain data.

### 4.8 What-If parameters (Stress Testing dashboard)

`Modeling → New parameter → Numeric range`:
- Name: `PD Multiplier (What-If)`
- Min 0.5, Max 5.0, Step 0.1, Default 1.0
- Add slicer to page

Repeat for `LGD Multiplier (What-If)` (Min 0.5, Max 2.0, Step 0.05, Default 1.0).

The DAX measure `[Stressed ECL (What-If)]` in the DAX library will automatically pick up these values.

---

## Phase 5 — Polish & Publish (60 min)

### 5.1 Navigation

- Add a left-side navigation bar with buttons for each dashboard
- Use page navigators (Insert → Buttons → Page navigator) for automatic syncing
- Sync the nav bar across all pages

### 5.2 Bookmarks

- Create bookmarks for: "Base Scenario", "Severe Scenario", "FY24 YTD", "Current Month"
- Add a bookmark selector to the relevant dashboards

### 5.3 Accessibility

- Add alt-text to all visuals
- Verify tab order: `View → Selection pane → Tab order`
- Ensure colour is not the only signal (icons + text accompany red/green)

### 5.4 Performance check

`View → Performance analyzer`:
- Start recording
- Click each page
- Verify each visual renders in <1 second
- For any visual >2 seconds, optimise the underlying measure (look for `FILTER(ALL(...))` patterns that could be `CALCULATE(..., REMOVEFILTERS(...))`)

### 5.5 Publish

`Home → Publish → Select workspace`

In the Power BI Service:
- Configure scheduled refresh (Settings → Datasets → Refresh)
- Set data source credentials
- For Indian FY display, ensure locale is set correctly in workspace settings

### 5.6 Subscriptions & Sharing

- Investor Reporting dashboard → Subscribe → LIC, SBI MF, HDFC Pension recipients (monthly cadence)
- Executive Overview → Subscribe → Risk Committee (weekly cadence)
- Trustee dashboard view → Subscribe → IDBI Trusteeship (monthly cadence)

### 5.7 Row-Level Security (RLS) — Optional

For investor-tier scoping:
1. `Modeling → Manage roles → New role "Senior Tranche Investor"`
2. DAX filter: `[TrancheID] = "TR-A"` on `dim_tranche`
3. Map specific user emails to this role in the Power BI Service

This prevents senior investors from seeing mezz/equity-specific data they don't have a need-to-know for.

---

## Phase 6 — Validation Checklist

Before declaring the build complete, verify:

- [ ] All 18 datasets loaded with correct row counts
- [ ] All relationships in `star_schema.md` are present and configured correctly
- [ ] All 110+ DAX measures created and validated
- [ ] All 7 dashboards built per `dashboard_specifications.md`
- [ ] Slicers sync across pages
- [ ] Drill-throughs work from Executive Overview → Loan Detail
- [ ] What-If parameters affect the Stress Testing measures in real time
- [ ] Cross-filtering works on each dashboard
- [ ] Tooltips show context on hover
- [ ] Page navigation works
- [ ] Performance: all pages render <3 seconds
- [ ] No DAX errors in any measure
- [ ] Currency, percentage, count formats correct everywhere
- [ ] Locale handles Indian FY correctly
- [ ] Published to Service successfully
- [ ] Scheduled refresh configured
- [ ] At least one subscription configured and tested
- [ ] RLS (if needed) tested with a non-admin user

---

## Maintenance Cadence

| Frequency | Action | Owner |
|---|---|---|
| Daily | `fact_dpd_snapshot` refresh | Data engineering / scheduled |
| Monthly | All facts refresh; Investor PDF export | Securitisation operations |
| Quarterly | PD/LGD recalibration; assumption review | Risk team |
| Annually | Stress scenario calibration review; rating agency reconciliation | Risk Committee |
| Ad hoc | Backup servicer test; trustee audit support | Trustee + Originator |

---

## Troubleshooting

| Symptom | Likely Cause | Fix |
|---|---|---|
| Measure returns BLANK | Filter context too restrictive | Wrap in `CALCULATE(..., ALL(...))` or check relationship direction |
| Slow page | Iterator over large table | Switch SUMX over fact to CALCULATE + SUM where possible |
| Stress dashboard not responding to scenario | `dim_scenario` filter not propagating | Verify `[Stressed ECL]` uses `SELECTEDVALUE(dim_scenario[ScenarioID])` not LASTNONBLANK |
| FY measures showing calendar-year buckets | DATESYTD missing "31/03" year-end | Add explicit year-end-date argument: `DATESYTD(dim_calendar[Date], "31/03")` |
| Sankey not rendering | Visual not enabled | `File → Options → Preview features → Enable Sankey` |
| Loan-grain drill-through shows all loans | Drill-through field not set | Verify `LoanID` is added to Drill-through pane on the target page |

---

End of implementation guide. A developer following this end-to-end can replicate the platform in a single working day.
