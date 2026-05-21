# Assumptions & Methodology

This document discloses every material assumption and methodological choice embedded in the Securitisation Risk Analytics platform. It is intended to be auditable: every measure can be traced to either a regulatory citation, an industry-standard convention, a synthetic-data design decision, or an explicit modelling judgement.

---

## 1. Source Data Provenance

| Dataset | Source | Treatment |
|---|---|---|
| `auto_loan_securitisation_data.csv` | User-supplied production extract | Loaded as-is into `fact_loan`, enriched with surrogate keys and band classifications |
| `dpd_snapshot_history.csv` | User-supplied monthly snapshot extract | Loaded as-is into `fact_dpd_snapshot`, extended with `SnapshotDateKey` |
| `dynamic_loss_monthly.csv` | User-supplied trustee monthly report extract | Loaded as-is into `fact_loss_monthly`, extended with `ReportingDateKey` |
| `static_pool_vintage_data.csv` | User-supplied static-pool extract (broader universe than the single trust) | Loaded as-is into `fact_vintage` — see reconciliation note below |
| All `dim_*` dimension tables | Generated for this engagement | Designed to be plausible for an Indian auto-ABS context, calibrated against RBI Master Direction (2021) and observed industry practice |
| `fact_tranche_cashflow.csv` | Computed | Derived from `fact_loss_monthly` cashflows using sequential-pay waterfall logic |
| `fact_waterfall_distribution.csv` | Computed | 9-step waterfall application of monthly collections |
| `fact_stress_results.csv` | Computed | Application of `dim_scenario` multipliers to base PD/LGD/EAD |
| `fact_economic_history.csv` | Synthetic | 48-month India macro indicators calibrated against RBI bulletin trends 2021-2024 |

### Reconciliation Note — Pool Size Discrepancy

`fact_loan` shows ₹317.78 Cr current balance across 500 loans. `fact_loss_monthly` shows BOP_Balance of approximately ₹54 Cr in the early months. These do not reconcile because:

- `fact_loan` is the **cut-off snapshot of one trust** (ZAAUTO2024-1) at 30-Oct-2024
- `fact_loss_monthly` represents **monthly aggregate dynamics**, and was supplied with values at a different scale of analysis (potentially a sub-pool or a different trust)
- `fact_vintage` covers 375 vintages from Q1 2021 onwards — a broader universe than the single trust represented in `fact_loan`

The platform treats these as **complementary lenses** rather than reconciliable totals. The Investor Reporting dashboard sources WAC/WAM/WALA from `fact_loan` (loan-grain truth), while CPR/CDR trend lines source from `fact_loss_monthly` (time-series dynamics).

---

## 2. IFRS 9 Expected Credit Loss Methodology

### 2.1 Three-Stage Classification

| Stage | Trigger | DPD Range | ECL Horizon | Source Field |
|---|---|---|---|---|
| Stage 1 | Performing, no SICR | 0–30 DPD | 12-month ECL | `fact_loan.IFRS9_Stage = "Stage 1"` |
| Stage 2 | Significant Increase in Credit Risk (SICR) | 31–90 DPD or CIBIL drop > 50 points | Lifetime ECL | `fact_loan.IFRS9_Stage = "Stage 2"` |
| Stage 3 | Credit-impaired | 90+ DPD, restructured, or default flag | Lifetime ECL, 100% loss recognition | `fact_loan.IFRS9_Stage = "Stage 3"` |

Triggers are computed at origination/initial recognition (`fact_loan` row creation) and recomputed monthly using `fact_dpd_snapshot`.

### 2.2 ECL Computation Formula

```
ECL_loan = PD_loan × LGD_loan × EAD_loan × Discount_Factor
```

Where:

- **PD (Probability of Default)** — Sourced from `fact_loan.PD_12Month` (Stage 1) or `fact_loan.PD_Lifetime` (Stage 2 & 3). PD term structure is calibrated externally and refreshed quarterly. Range: 0.005 (Stage 1 best) to 1.000 (Stage 3 confirmed default).

- **LGD (Loss Given Default)** — Sourced from `fact_loan.LGD`. Calibrated as `1 - (Recovery_Rate × (1 - Resolution_Cost_%))`. For auto loans backed by depreciating collateral, baseline LGD ranges 25–45%. Range: 0.10–0.80.

- **EAD (Exposure at Default)** — For installment-amortising auto loans, EAD = current outstanding principal balance (`fact_loan.OutstandingPrincipal`). For revolving facilities (not applicable here), EAD would include credit conversion factor on undrawn amounts.

- **Discount Factor** — Effective Interest Rate (EIR) of the loan applied to expected loss timing. For 12-month ECL on Stage 1 loans, discount impact is small (<2%) and treated as immaterial. For Lifetime ECL on Stage 2/3, discount factor is built into the calibrated LGD.

### 2.3 ECL Validation

The DAX measure `[ECL Calculated]` reproduces the formula `SUMX(fact_loan, PD × LGD × EAD)` and is reconciled against `[Total ECL]` which sums the pre-loaded `fact_loan.ECL` field. Material divergence (>1%) between these two measures flags a model-data integrity issue.

### 2.4 Forward-Looking Information (FLI)

IFRS 9 paragraph 5.5.17 requires inclusion of forward-looking macroeconomic information. The platform implements this through `dim_scenario`:

- Base scenario uses point estimates from `fact_loan.PD_12Month` and `fact_loan.PD_Lifetime` as-supplied
- Forward-looking scenarios apply PD and LGD multipliers reflecting probability-weighted future states
- A weighted-average ECL across scenarios (Base 60%, Mild 20%, Moderate 15%, Severe 5%) can be computed for regulatory disclosure — measure `[Weighted ECL with FLI]` available in the DAX library

---

## 3. Stress Test Scenario Calibration

| Scenario | PD Multiplier | LGD Multiplier | GDP Shock | Repo Rate Shock | Unemployment Shock | Calibration Anchor |
|---|---|---|---|---|---|---|
| Base | 1.0× | 1.0× | 0 bps | 0 bps | 0 bps | Current macro |
| Mild Recession | 1.3× | 1.1× | -100 bps | +25 bps | +50 bps | Single quarter slowdown |
| Moderate Slowdown | 1.8× | 1.25× | -200 bps | +50 bps | +120 bps | 2019 slowdown analogue |
| Severe Recession | 2.8× | 1.45× | -350 bps | +100 bps | +250 bps | 2020 COVID shock analogue |
| Crisis | 4.5× | 1.75× | -500 bps | +200 bps | +400 bps | 2008 GFC + 2018 IL&FS analogue |

**Calibration logic:** Multipliers are calibrated such that the Severe scenario reproduces approximately the realised default-rate jump observed in Indian retail auto-loan pools during the H1 2020 COVID-19 moratorium period (CDR ~3.5% vs. baseline ~1.0%, per CRISIL Securitisation Reports). The Crisis scenario is calibrated to be approximately 1.6× the severity of Severe — consistent with the discontinuous jump observed in 2008-era US subprime and 2018 Indian NBFC funding conditions.

**Sensitivity overlay:** The What-If PD Multiplier (0.5×–5.0×) and LGD Multiplier (0.5×–2.0×) parameters on the Stress Testing dashboard allow user-defined overrides without rebuilding the scenario table.

**Limitations:** Multipliers are applied uniformly across the pool. Real stress events show heterogeneous effects (e.g., subprime borrowers default at multiples of prime). Future iterations could refine this with segment-specific multipliers driven by CIBIL band.

---

## 4. Synthetic Dimension Data Design

The following tables were generated for this engagement because the source CSVs did not include them. All values are plausible for an Indian auto-ABS context as at Q4 2024.

### `dim_pool` (ZAAUTO2024-1)

- Pool name "Zenith Auto Receivables Trust 2024 Series 1" — fictional, designed to follow Indian originator naming conventions
- Trustee "IDBI Trusteeship Services Limited" — real institution commonly serving Indian securitisations
- Ratings AAA(SO)/AA(SO)/BBB(SO) — Structured Obligation rating notation per CRISIL/ICRA convention
- Regulatory framework "RBI Master Direction (Securitisation of Standard Assets) Directions, 2021" — actual current regulation

### `dim_tranche` (Three-tranche structure)

- 80/12/8 split — typical for Indian auto-ABS where the senior tranche needs ~20% subordination to achieve AAA(SO)
- Senior coupon 8.25% — calibrated against G-Sec 10Y + ~75-100 bps spread for AAA(SO) auto-ABS in Aug 2024
- Mezzanine coupon 10.50% — AA(SO) spread approximately 225 bps over senior
- Equity tranche 14% expected return — residual after waterfall; not a fixed coupon

### `dim_investor` (8 investors)

- LIC, SBI MF, HDFC Pension, Nomura — typical senior-tranche allocation for Indian auto-ABS deals
- ICICI Pru, Edelweiss AIF, Goldman Sachs AM — typical mezzanine allocation seeking higher yield
- Zenith Capital holding 100% of equity tranche — satisfies RBI MRR (Minimum Retention Requirement) of 5–10% depending on structure
- FPI flag set for Nomura (Japan) and Goldman Sachs (US) — enables FPI Allocation % measure

### `dim_servicer` (3 servicers)

- HDFC Bank, ICICI Bank — actual major Indian banks active in auto financing
- Bajaj Finance — actual major Indian NBFC active in auto financing
- All rated AAA / AA+ — calibrated against actual long-term ratings of these institutions as at 2024
- Backup Servicer "SBI Cap Trustee" — common practice in Indian securitisations

### `dim_calendar` (4,383 rows, 2021–2032)

- Indian Financial Year (April–March) — fiscal year column populated as "FY2024-25" for April 2024–March 2025
- Fiscal Quarter labels Q1 (Apr-Jun), Q2 (Jul-Sep), Q3 (Oct-Dec), Q4 (Jan-Mar)
- Working day flags exclude Saturdays and Sundays; bank holidays not modelled in this iteration

### `dim_scenario` (5 scenarios)

See section 3 above for calibration anchors.

### `dim_economic_indicator` (8 indicators)

GDP growth, CPI inflation, Repo rate, Unemployment, IIP, Auto sales, Used vehicle price index, INR/USD exchange rate — chosen for their direct relevance to auto-loan default and recovery behaviour.

---

## 5. Banded Field Logic

Several dimensional bands are constructed at ETL time for slicing. Cut-offs:

| Field | Band Logic |
|---|---|
| `CIBILBand_Orig` / `CIBILBand_Curr` | <600: "Subprime"; 600–649: "Near Prime"; 650–699: "Prime"; 700–749: "Super Prime"; 750+: "Excellent" |
| `LTV_Band` | <40%: "Low"; 40–60%: "Moderate"; 60–80%: "High"; 80%+: "Very High" |
| `DTI_Band` | <0.20: "Low"; 0.20–0.35: "Moderate"; 0.35–0.50: "High"; 0.50+: "Stressed" |
| `IncomeBand` | <₹3L: "Low"; ₹3–6L: "Lower-Mid"; ₹6–12L: "Mid"; ₹12–25L: "Upper-Mid"; ₹25L+: "High" |
| `AgeBand` | <25, 25–35, 36–45, 46–55, 56+ |
| `StateTier` | RBI Tier-1 (metros), Tier-2, Tier-3 based on state population/economic profile |

---

## 6. Indian Regulatory Conventions Applied

- **DPD bucketing:** 0, 1-30, 31-60, 61-90, 90+ (RBI standard)
- **NPA recognition:** 90+ DPD = Sub-Standard Asset (RBI IRACP norms)
- **Asset classification:** Standard (0-89 DPD), Sub-Standard (90-365), Doubtful (365+), Loss (specific identification)
- **Securitisation framework:** RBI Master Direction — Reserve Bank of India (Securitisation of Standard Assets) Directions, 2021
- **MRR (Minimum Retention Requirement):** 5% for pools with residual maturity ≤24 months, 10% for >24 months
- **MHP (Minimum Holding Period):** Originator must hold loans for minimum 9 months (auto loans) before securitising

---

## 7. Known Limitations & Future Enhancements

1. **PD term structure:** Currently a single 12-month and lifetime PD per loan. Production-grade implementation would carry a PD curve over the loan's life with vintage- and segment-specific shapes.

2. **LGD point estimate:** Currently a single LGD per loan. Production implementation would model recovery as a function of time-since-default, collateral type, and resolution channel (repossession vs. legal vs. settlement).

3. **Prepayment optionality:** CPR is computed but not used to discount future cash flows. A full Effective Interest Rate / yield-to-maturity computation would model prepayment as a function of rates and seasoning.

4. **Cure rates:** Stage 2 borrowers can cure back to Stage 1 in IFRS 9 (subject to 12-month probation). Current implementation tracks current stage only; historical migration is in `fact_dpd_snapshot` but cure economics are not modelled.

5. **Cross-collateralisation:** Not applicable to this pool (each auto loan has one vehicle). Would matter for residential MBS pools.

6. **Behavioural maturity vs. contractual:** WAM uses contractual maturity. Behavioural maturity adjustments based on observed prepayment would shorten WAM by ~6-10 months.

7. **Recovery timing:** Recovery cash flows are recognised when realised, not when estimated. IFRS 9 best practice would discount expected future recoveries.

8. **Scenario probability weights:** Currently uniform across the dashboard. Production use should expose these as parameters for the FLI overlay.

---

## 8. Audit Trail

Every DAX measure carries an inline comment naming the source field(s) and computation logic. Every dimension table carries the design rationale described in section 4. Every fact table that is computed (`fact_tranche_cashflow`, `fact_waterfall_distribution`, `fact_stress_results`) is reproducible from the Python ETL script `build_supplementary_data.py` against the supplied source CSVs.

A user with access to the source data, the ETL script, and the DAX library should be able to fully reproduce every figure on every dashboard without recourse to undocumented logic.

*All assumptions disclosed in this document are subject to periodic review by the Originator's Risk Committee and updated on a quarterly cycle.*
