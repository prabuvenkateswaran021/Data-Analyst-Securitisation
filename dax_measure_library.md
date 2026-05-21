# MatRisk AI · DAX Measure Library

**Pool:** `ZAAUTO2024-1`  
**Measure count:** 139  

## 01. Calendar & Date Helpers

| Measure | Format | Description |
|---|---|---|
| `[Latest Snapshot Date]` | `—` | Most recent snapshot date present in the DPD snapshot table. |
| `[Latest Reporting Date]` | `—` | Most recent reporting date present in the monthly loss table. |
| `[Selected Period Label]` | `—` | Human-readable label for the currently selected period. |

## 02. Portfolio Core

| Measure | Format | Description |
|---|---|---|
| `[Loan Count]` | `#,##0` |  |
| `[Borrower Count]` | `#,##0` |  |
| `[Original Pool Balance]` | `"₹"#,0;("₹"#,0)` |  |
| `[Current Pool Balance]` | `"₹"#,0;("₹"#,0)` |  |
| `[Total EAD]` | `"₹"#,0;("₹"#,0)` |  |
| `[Pool Factor]` | `0.0000` | Current outstanding ÷ original — pool amortisation indicator. |
| `[Avg Loan Size]` | `"₹"#,0;("₹"#,0)` |  |
| `[Avg Original Term Months]` | `0.0" m"` |  |
| `[Avg Months on Book]` | `0.0" m"` |  |
| `[Pool Balance at Snapshot]` | `"₹"#,0;("₹"#,0)` | Sum of current balance across loans at the latest snapshot. |

## 03. Weighted Averages

| Measure | Format | Description |
|---|---|---|
| `[WAC %]` | `0.00%` | Weighted average coupon (balance-weighted). |
| `[WAM Months]` | `0.0" m"` | Weighted average remaining maturity (months). |
| `[WALA Months]` | `0.0" m"` | Weighted average loan age (months on book). |
| `[Weighted Avg LTV %]` | `0.00%` | Balance-weighted current LTV ratio. |
| `[Weighted Avg DTI %]` | `0.00%` | Balance-weighted debt-to-income. |
| `[Weighted Avg CIBIL]` | `0` | Balance-weighted CIBIL score. |
| `[Portfolio Yield %]` | `0.00%` | Gross asset yield (alias for WAC); net yield deducts servicer + trustee fees. |

## 04. Delinquency & DPD Buckets

| Measure | Format | Description |
|---|---|---|
| `[Loans 30+ DPD Count]` | `#,##0` |  |
| `[Balance 30+ DPD]` | `"₹"#,0;("₹"#,0)` |  |
| `[30+ DPD %]` | `0.00%` |  |
| `[Loans 60+ DPD Count]` | `#,##0` |  |
| `[Balance 60+ DPD]` | `"₹"#,0;("₹"#,0)` |  |
| `[60+ DPD %]` | `0.00%` |  |
| `[Loans 90+ DPD Count]` | `#,##0` |  |
| `[Balance 90+ DPD]` | `"₹"#,0;("₹"#,0)` |  |
| `[90+ DPD %]` | `0.00%` |  |
| `[Delinquency Rate %]` | `0.00%` | Share of loans that are 30+ days past due (loan count basis). |
| `[NPA Balance]` | `"₹"#,0;("₹"#,0)` | Non-performing balance per RBI classification at latest snapshot. |
| `[NPA %]` | `0.00%` |  |
| `[GNPA Ratio %]` | `0.00%` | Gross NPA ratio — alias of NPA % retained for regulatory cross-referencing. |
| `[Net NPA Balance]` | `"₹"#,0;("₹"#,0)` | NPA balance net of Stage-3 ECL provisions (floored at zero). |
| `[Net NPA %]` | `0.00%` |  |

## 05. Default & Loss

| Measure | Format | Description |
|---|---|---|
| `[Defaulted Loan Count]` | `#,##0` |  |
| `[Default Rate %]` | `0.00%` |  |
| `[Total Gross Loss]` | `"₹"#,0;("₹"#,0)` |  |
| `[Total Net Loss]` | `"₹"#,0;("₹"#,0)` |  |
| `[Gross Loss Rate %]` | `0.00%` |  |
| `[Net Loss Rate %]` | `0.00%` |  |
| `[Monthly Default Rate %]` | `0.000%` |  |
| `[CDR Annualised %]` | `0.00%` | Annualised constant default rate: 1 − (1 − MDR)^12. |

## 06. Recovery

| Measure | Format | Description |
|---|---|---|
| `[Total Recovery]` | `"₹"#,0;("₹"#,0)` |  |
| `[Recovery Rate %]` | `0.00%` |  |
| `[Monthly Recovery]` | `"₹"#,0;("₹"#,0)` |  |

## 07. Prepayment (SMM, CPR)

| Measure | Format | Description |
|---|---|---|
| `[Total Prepayment]` | `"₹"#,0;("₹"#,0)` |  |
| `[Prepayment Rate %]` | `0.00%` |  |
| `[SMM Avg %]` | `0.000%` | Single Monthly Mortality — share of EOP balance prepaid per month. |
| `[CPR Annualised %]` | `0.00%` |  |
| `[CPR Calc %]` | `0.00%` | CPR derived from SMM as a cross-check on the reported CPR. |

## 08. IFRS 9 Staging & ECL

| Measure | Format | Description |
|---|---|---|
| `[Stage 1 Loan Count]` | `#,##0` |  |
| `[Stage 1 Balance]` | `"₹"#,0;("₹"#,0)` |  |
| `[Stage 1 EAD]` | `"₹"#,0;("₹"#,0)` |  |
| `[Stage 1 ECL]` | `"₹"#,0;("₹"#,0)` |  |
| `[Stage 2 Loan Count]` | `#,##0` |  |
| `[Stage 2 Balance]` | `"₹"#,0;("₹"#,0)` |  |
| `[Stage 2 EAD]` | `"₹"#,0;("₹"#,0)` |  |
| `[Stage 2 ECL]` | `"₹"#,0;("₹"#,0)` |  |
| `[Stage 3 Loan Count]` | `#,##0` |  |
| `[Stage 3 Balance]` | `"₹"#,0;("₹"#,0)` |  |
| `[Stage 3 EAD]` | `"₹"#,0;("₹"#,0)` |  |
| `[Stage 3 ECL]` | `"₹"#,0;("₹"#,0)` |  |
| `[Total ECL]` | `"₹"#,0;("₹"#,0)` |  |
| `[ECL Coverage %]` | `0.00%` | Portfolio-level ECL ÷ EAD coverage. |
| `[Stage 3 Coverage %]` | `0.00%` | Stage-3 ECL as a share of Stage-3 EAD — impairment intensity. |
| `[Weighted Avg PD %]` | `0.00%` | EAD-weighted probability of default. |
| `[Weighted Avg LGD %]` | `0.00%` | EAD-weighted loss given default. |
| `[ECL Calculated]` | `"₹"#,0;("₹"#,0)` | Validation: live PD × LGD × EAD vs. stored ECL_Provision. |
| `[Stage Migration Net %]` | `0.00%` | Share of loans not in Stage 1. |
| `[12-Month ECL]` | `"₹"#,0;("₹"#,0)` | 12-month ECL bucket per IFRS 9 §5.5.5 (Stage 1). |
| `[Lifetime ECL]` | `"₹"#,0;("₹"#,0)` | Lifetime ECL bucket per IFRS 9 §5.5.3 (Stages 2 & 3). |

## 09. Stress Testing

| Measure | Format | Description |
|---|---|---|
| `[Selected Scenario]` | `—` |  |
| `[Scenario PD Multiplier]` | `0.00` |  |
| `[Scenario LGD Multiplier]` | `0.00` |  |
| `[Scenario Recovery Haircut %]` | `0.00%` |  |
| `[Stressed ECL]` | `"₹"#,0;("₹"#,0)` | Live-stressed ECL with PD & LGD caps at 100%. |
| `[ECL Increase from Stress]` | `"₹"#,0;("₹"#,0)` |  |
| `[ECL Increase %]` | `0.00%` |  |
| `[Stressed ECL by Stage]` | `"₹"#,0;("₹"#,0)` |  |
| `[Stressed Loss to Senior Tranche]` | `"₹"#,0;("₹"#,0)` | Stressed loss absorbed by tranche TR-A (Senior). |
| `[Stressed Loss to Mezz Tranche]` | `"₹"#,0;("₹"#,0)` | Stressed loss absorbed by tranche TR-B (Mezz). |
| `[Stressed Loss to Equity Tranche]` | `"₹"#,0;("₹"#,0)` | Stressed loss absorbed by tranche TR-C (Equity). |

## 10. Tranche & Waterfall

| Measure | Format | Description |
|---|---|---|
| `[Tranche Original Balance]` | `"₹"#,0;("₹"#,0)` |  |
| `[Tranche EOP Balance]` | `"₹"#,0;("₹"#,0)` |  |
| `[Tranche Paydown %]` | `0.00%` |  |
| `[Cumulative Tranche Interest Paid]` | `"₹"#,0;("₹"#,0)` |  |
| `[Cumulative Tranche Principal Paid]` | `"₹"#,0;("₹"#,0)` |  |
| `[Cumulative Tranche Loss]` | `"₹"#,0;("₹"#,0)` |  |
| `[Credit Enhancement %]` | `0.00%` | Subordination remaining for the senior tranche. |
| `[Waterfall Amount]` | `"₹"#,0;("₹"#,0)` |  |
| `[Total Collections]` | `"₹"#,0;("₹"#,0)` |  |
| `[Excess Spread]` | `"₹"#,0;("₹"#,0)` |  |
| `[Cumulative Excess Spread]` | `"₹"#,0;("₹"#,0)` |  |

## 11. Investor Reporting

| Measure | Format | Description |
|---|---|---|
| `[Total Invested by Investors]` | `"₹"#,0;("₹"#,0)` |  |
| `[Investor Count]` | `#,##0` |  |
| `[Senior Investor Allocation]` | `"₹"#,0;("₹"#,0)` |  |
| `[Mezz Investor Allocation]` | `"₹"#,0;("₹"#,0)` |  |
| `[Equity Investor Allocation]` | `"₹"#,0;("₹"#,0)` |  |
| `[FPI Allocation]` | `"₹"#,0;("₹"#,0)` |  |
| `[FPI Allocation %]` | `0.00%` |  |

## 12. Collection Efficiency & Ops

| Measure | Format | Description |
|---|---|---|
| `[Collection Efficiency %]` | `0.00%` |  |
| `[Avg Collection Efficiency %]` | `0.00%` |  |
| `[Avg Monthly Billing]` | `"₹"#,0;("₹"#,0)` |  |
| `[Cure Count]` | `#,##0` |  |
| `[Repossession Count]` | `#,##0` |  |
| `[Write-Off Count]` | `#,##0` |  |

## 13. Vintage / Static Pool

| Measure | Format | Description |
|---|---|---|
| `[Vintage Cumulative Net Loss %]` | `0.00%` |  |
| `[Latest Vintage Net Loss %]` | `0.00%` |  |
| `[Vintage Pool Factor]` | `0.0000` |  |
| `[Vintage Marginal Loss Rate]` | `0.000%` |  |
| `[Vintage Loss @ 12 MOB]` | `0.00%` | Cumulative net loss at 12 months on book. |
| `[Vintage Loss @ 24 MOB]` | `0.00%` | Cumulative net loss at 24 months on book. |

## 14. Roll-Rate & Transition

| Measure | Format | Description |
|---|---|---|
| `[Loans Forward Rolled]` | `#,##0` |  |
| `[Loans Backward Rolled]` | `#,##0` |  |
| `[Loans Static]` | `#,##0` |  |
| `[Forward Roll Rate %]` | `0.00%` | Forward rolls ÷ delinquent population at prior snapshot. |
| `[Cure Rate %]` | `0.00%` |  |
| `[Roll 30 to 60 %]` | `0.00%` | Transition probability 1-29 DPD → 30-59 DPD. |
| `[Roll 60 to 90 %]` | `0.00%` | Transition probability 30-59 DPD → 60-89 DPD. |

## 15. Time Intelligence

| Measure | Format | Description |
|---|---|---|
| `[Net Loss MTD]` | `"₹"#,0;("₹"#,0)` |  |
| `[Net Loss YTD]` | `"₹"#,0;("₹"#,0)` | Year-to-date net loss, Indian fiscal year (1 Apr – 31 Mar). |
| `[Net Loss QTD]` | `"₹"#,0;("₹"#,0)` |  |
| `[Pool Balance Prior Month]` | `"₹"#,0;("₹"#,0)` |  |
| `[Pool Balance MoM Change %]` | `0.00%` |  |
| `[Cumulative Net Loss]` | `"₹"#,0;("₹"#,0)` |  |
| `[Rolling 12M Default Rate %]` | `0.000%` |  |

## 16. Ranking & Dynamic

| Measure | Format | Description |
|---|---|---|
| `[State Rank by ECL]` | `#,##0` |  |
| `[Top 5 Risky States ECL]` | `"₹"#,0;("₹"#,0)` |  |
| `[Servicer Rank by Balance]` | `#,##0` |  |
| `[Top 10 Borrower Share %]` | `0.00%` | Concentration ratio — top 10 borrower balance share. |

## 17. Risk-Adjusted Returns & Yield

| Measure | Format | Description |
|---|---|---|
| `[Annualised Gross Interest Revenue]` | `"₹"#,0;("₹"#,0)` |  |
| `[Expected Loss (Annual)]` | `"₹"#,0;("₹"#,0)` | One-year EL approximation for RAROC denominator. |
| `[Risk-Adjusted Return on Assets %]` | `0.00%` |  |
| `[Tranche Coupon Revenue]` | `"₹"#,0;("₹"#,0)` |  |
| `[Tranche Yield Realised %]` | `0.00%` |  |

## Aux. Heat-Map Conditional Formatting

| Measure | Format | Description |
|---|---|---|
| `[Heat 30+ DPD Colour]` | `—` | Conditional-format colour for the 30+ DPD KPI. |
| `[Heat Stage Mix Colour]` | `—` | Conditional-format colour driven by Stage-3 balance share. |

## Aux. Dynamic KPI Headlines

| Measure | Format | Description |
|---|---|---|
| `[KPI Headline Risk Status]` | `—` | Traffic-light commentary card driven by stressed ECL coverage. |
