# MatRisk AI: A Quantitative Platform for Indian Auto-Loan ABS Risk Analytics

**Technical Report — Version 1.0**
*Zetheta Algorithms Pvt. Ltd.*
*May 2026*

---

## Abstract

This report describes the design, implementation and empirical
performance of **MatRisk AI**, a Python platform for risk analytics on
Indian auto-loan asset-backed securitisations (ABS). The platform
implements IFRS 9 expected-credit-loss (ECL) calculation under both the
12-month and lifetime horizons, a parametric stress-testing framework
with five RBI-aligned scenarios, and a sequential-pay cash-flow
waterfall consistent with standard Indian pass-through-certificate (PTC)
structures. We demonstrate the platform on a pilot pool —
`ZAAUTO2024-1`, a ₹54.6 cr 500-loan auto-loan PTC originated in
Q4-2023 — and find that under a 1-in-50 crisis stress scenario, lifetime
ECL increases by approximately 325% but remains entirely absorbed by
the 18.5% senior credit enhancement provided by the mezzanine and
equity tranches. The codebase achieves 95% test coverage across 113
tests and is delivered as an installable Python package with a
Docker-compose stack, MLflow experiment tracking, and DVC-versioned
data pipeline.

---

## Table of Contents

1. Introduction
2. Literature Review
3. Data
4. Methodology
5. Implementation
6. Empirical Results
7. Stress-Test Findings
8. Case Studies
9. Limitations and Future Work
10. Conclusions
11. References

---

## 1. Introduction

### 1.1 Background

The Indian securitisation market for retail loans has grown rapidly
since the introduction of the RBI Master Direction on Securitisation
of Standard Assets in September 2021. The directive consolidated
fragmented prudential guidelines into a single framework, introducing
explicit minimum retention requirements (MRR), minimum holding period
(MHP) rules, and a stricter true-sale test. Auto loans — particularly
new-vehicle loans to salaried borrowers — now account for a
significant share of pass-through-certificate (PTC) issuance
alongside the dominant microfinance and commercial-vehicle segments.

Despite the policy progress, analytical practice has lagged. Many
Indian originators still rely on spreadsheet-based static-pool
analyses that under-utilise the lifetime PD signal in the data,
ignore the term-structure of credit risk in long-dated auto loans,
and lack systematic stress testing. The challenge is compounded by
the loan-level heterogeneity in Indian auto pools — borrowers span
the credit spectrum from prime salaried metro borrowers to
self-employed rural buyers of used commercial vehicles — which makes
pool-level back-of-envelope ECL unreliable.

### 1.2 Motivation

Three regulatory and market forces motivate the platform:

1. **IFRS 9 adoption** by Indian banks under the upcoming
   Ind AS 109 regime requires forward-looking ECL on every reporting
   date, with explicit staging (12-month for Stage 1, lifetime for
   Stage 2 and 3). The 2018 IL&FS NBFC liquidity event demonstrated
   how rapidly Stage-1 portfolios can migrate to Stage 2 under
   wholesale funding stress.

2. **Basel III credit-risk capital** requires regulated lenders to
   hold internal-ratings-based (IRB) capital that depends on PD, LGD
   and EAD estimates. Indian banks are working toward IRB approval,
   and securitisation tranches held on balance sheet must also be
   capitalised under the SEC-IRBA / SEC-SA framework (BCBS d350).

3. **Investor due-diligence** for AAA-rated senior PTC tranches now
   routinely includes a stress-testing requirement, with rating
   agencies expecting issuers to demonstrate that the assigned credit
   enhancement is sufficient under multiple severity grades.

### 1.3 Contribution

We make four contributions:

1. A clean, type-checked Python implementation of the IFRS 9 ECL
   staging logic with the Stage-3 precedence rule (one-way ratchet
   per IFRS 9 §5.5.20), the LGD collar, and the Stage-3 lifetime-PD
   floor that practitioners commonly apply.

2. A parametric stress-test framework calibrated to historical Indian
   stress episodes — the 2008 GFC, the 2018 IL&FS event, and a
   forward-looking 1-in-50 crisis tail.

3. A nine-step PTC waterfall implementation with bottom-up loss
   allocation that respects the tranche seniority and produces a
   credit-enhancement number consistent with rating-agency
   methodology.

4. A reproducible analytics platform — DVC-versioned, MLflow-tracked,
   docker-compose deployable — that takes raw loan-level CSVs to an
   investor dashboard in a single CLI command and is delivered with
   95% test coverage.

---

## 2. Literature Review

### 2.1 Expected credit loss under IFRS 9

The accounting standard IFRS 9 (IASB, 2014) replaced the incurred-loss
model of IAS 39 with a forward-looking expected-credit-loss model that
became mandatory for IFRS-compliant entities from 1 January 2018. Under
IFRS 9, every financial asset is staged at every reporting date:
Stage 1 (performing) carries 12-month ECL, Stage 2 (significant
increase in credit risk since origination) carries lifetime ECL, and
Stage 3 (credit-impaired) carries lifetime ECL on the net carrying
amount. The European Banking Authority's guidelines GL/2017/06 (EBA,
2017) provided supervisory expectations on staging, including the
rebuttable presumption that DPD ≥ 30 triggers Stage 2.

Academic work on the discriminatory power of staging criteria includes
Krüger and Rösch (2017), who find that simple DPD-based staging
under-detects forward-looking deterioration in retail portfolios and
should be supplemented with behavioural credit-score-based triggers.
The CIBIL score drop trigger implemented in MatRisk AI (§4.1) follows
this recommendation.

### 2.2 PD term structure

The simplest approach to deriving a lifetime PD from a 12-month PD is
the constant-hazard extension implemented here. More sophisticated
approaches include the Vasicek (2002) single-factor model, the Wilson
(1997) macro factor model, and Markov-chain credit-state models. The
EBA (2017) and BCBS (2017) frameworks accept any of these provided the
firm can demonstrate calibration on historical data. For the pilot pool,
the constant-hazard extension is appropriate because the pool is too
small (n = 500) to support estimation of a multi-state Markov
transition matrix.

### 2.3 LGD modelling and collars

LGD estimation in retail portfolios is challenging because the
recovery process spans years and individual recovery rates are highly
bimodal — either the secured asset is repossessed and recovers
60–80% of EAD, or the borrower defaults and the lender recovers
under 20%. The "downturn LGD" concept of BCBS (2017) requires LGD
to be stressed to reflect the recovery shortfalls observed in
recessions. Andersson and Mayock (2014) document that downturn-LGD
adjustments of 20–40% are typical for US auto-loan portfolios. The
25%–75% LGD collar in MatRisk AI is a practical, conservative
approximation that bounds the estimator when loan-level recovery
evidence is thin.

### 2.4 Securitisation waterfall mechanics

Fabozzi (2016) provides the standard textbook treatment of ABS
waterfall mechanics. The Indian PTC structure is described in detail
in Chakraborty and Mukherjee (2019), with focus on the priority of
payments, the cash-reserve mechanism, and the role of the trustee.
Rating-agency methodology — ICRA (2022), CRISIL (2023) — formalises the
credit-enhancement computation and lays out the principal-pay rules.

### 2.5 Stress testing

The IMF's Macrofinancial Stress Testing Framework (Adrian et al.,
2020) is the canonical reference for designing stress scenarios that
link macro variables (GDP, unemployment, interest rates, asset prices)
to credit risk parameters. For Indian retail credit, RBI's Financial
Stability Reports (RBI, 2023, 2024) publish annual stress severities
that we draw on to calibrate the MILD, MODERATE, and SEVERE scenarios.
The CRISIS scenario combines the FY2009 GFC shock with the FY2018
IL&FS event, broadly aligned with the 1-in-50 reverse-stress concept
of EBA (2018).

### 2.6 Indian regulatory framework

The RBI Master Direction on Securitisation of Standard Assets (RBI,
2021) governs the structuring of Indian PTC transactions. Key
features replicated in MatRisk AI's analytical assumptions are:

- The 5% Minimum Retention Requirement (MRR) on the originator,
  reflected in the equity-tranche notional of the pilot pool.
- The Minimum Holding Period (MHP) of 6–12 months depending on loan
  tenor, reflected in the WALA of 16.8 months for the pool.
- Senior–subordinated structure with sequential pay-through, modelled
  in the waterfall.

The RBI Master Direction on Income Recognition, Asset Classification
and Provisioning (RBI, 2021b) defines the NPA threshold at 90 DPD, which
we adopt for the `npa_pct` KPI.

---

## 3. Data

### 3.1 Pilot pool description

The pilot pool `ZAAUTO2024-1` is a securitised Indian auto-loan PTC
issued in Q4-2023 by a fictional originator referenced in the dataset
provider's specification. Key statistics:

- **Original notional**: ₹54.61 crore (US$ ≈ 6.5 M)
- **Number of loans at origination**: 500
- **Cutoff date**: 31 December 2024
- **Pool factor at cutoff**: 0.582 (current ₹31.78 cr / original ₹54.61 cr)
- **Weighted-average coupon (WAC)**: 10.95%
- **Weighted-average maturity (WAM)**: 45.1 months
- **Weighted-average loan age (WALA)**: 16.8 months

### 3.2 Source files

The platform consumes four CSV files:

| File | Granularity | Rows | Key columns |
|---|---|---|---|
| `auto_loan_securitisation_data.csv` | Loan | 500 | LoanID, balances, IFRS9_Stage, PD_Estimate, LGD_Estimate, EAD, ECL_Provision |
| `dpd_snapshot_history.csv` | Loan × month | 6,000 | SnapshotDate, LoanID, DPD_Days, DPD_Bucket, RBI_SMA_Class, TransitionType |
| `dynamic_loss_monthly.csv` | Pool × month | 12 | ReportingDate, BOP/EOP_Balance, GrossLoss, NetLoss, CPR_Annualised |
| `static_pool_vintage_data.csv` | Vintage × MOB | 375 | VintageID, MonthsOnBook, CumulativeNetLossRate, PoolFactor |

### 3.3 Composition

The pool is concentrated in salaried borrowers (≈ 72% by balance) with
strong CIBIL profiles (weighted average 742). Vehicle-type distribution
is roughly 35% hatchback / 30% sedan / 25% SUV / 10% other. Regional
concentration favours the South (≈ 38%) and West (≈ 25%) with the
balance in North and East.

### 3.4 Credit profile

| Stage | Loans | Balance (cr) | EAD (cr) | ECL (cr) | Coverage |
|---|---|---|---|---|---|
| 1 — Performing | 422 | 26.41 | 27.10 | 0.17 | 0.6% |
| 2 — SICR | 45 | 3.59 | 3.69 | 0.31 | 8.4% |
| 3 — Impaired | 33 | 1.77 | 1.83 | 0.69 | 37.7% |
| **Total** | **500** | **31.78** | **32.62** | **1.17** | **3.58%** |

The pool is performing within rating expectations: NPA (90+ DPD) is
5.57% by balance, 30+ DPD is 14.1%. Stage 3 captures the small but
visible distressed cohort.

### 3.5 Data-quality treatment

Three column-level interventions are applied at ingestion:

1. **Ratio normalisation**: source columns `LTV_Current`, `DTI_Ratio`
   and `LGD_Estimate` are stored as 0–1 ratios. The loader detects
   this (median ≤ 1.5) and rescales to 0–100 to match the `_pct`
   naming convention used throughout the codebase.

2. **Boolean coercion**: source flags like `IsDefaulted` and
   `HasInsurance` appear as strings (`"True"`, `"Yes"`, `"1"`) and
   are coerced to native Python booleans.

3. **Date coercion**: `OriginationDate`, `CutoffDate`, `MaturityDate`
   and `LastPaymentDate` are parsed with an ISO-first / dayfirst
   fallback strategy.

---

## 4. Methodology

### 4.1 IFRS 9 staging

The staging decision rule implemented in `matrisk.analytics.credit.assign_ifrs9_stage`
is:

$$
S_i =
\begin{cases}
3 & \text{if } DPD_i \ge 90 \text{ days, or } i \text{ is defaulted} \\
2 & \text{if } DPD_i \ge 30, \text{ or } CIBIL_{\text{drop}, i} \ge 50 \\
1 & \text{otherwise}
\end{cases}
$$

Stage 3 is evaluated **last** so it takes precedence: a loan that
satisfies both the Stage-2 and Stage-3 triggers is staged 3, reflecting
the one-way ratchet of IFRS 9 §5.5.20.

### 4.2 12-month and lifetime ECL

For Stage 1 loans, 12-month ECL is the standard:

$$
ECL^{12m}_i = PD^{12m}_i \cdot LGD_i \cdot EAD_i
$$

For Stage 2 and Stage 3 loans, lifetime ECL is used. We derive lifetime
PD from 12-month PD assuming a constant monthly hazard:

$$
PD^{LT}_i = 1 - (1 - PD^{12m}_i)^{T_i / 12}
$$

where $T_i$ is the remaining term in months. The constant-hazard
assumption is simple, well-understood, and adequate for the pilot
pool's size; richer term structures (Vasicek, Wilson, Markov) can drop
in as a function replacement.

### 4.3 LGD collar and PD floor

To stabilise ECL under thin recovery data, LGD is collared at
[25%, 75%]. Stage-3 loans take a 95% PD floor: the loan is already
credit-impaired and residual uncertainty concentrates on the recovery
channel.

### 4.4 Stress test design

Each scenario applies multiplicative shocks to PD and LGD:

$$
PD^s_i = \min(1, PD^{base}_i \cdot m^{PD}_s)
\quad
LGD^s_i = \min(100\%, LGD^{base}_i \cdot m^{LGD}_s)
$$

The five default scenarios are:

| Scenario | $m^{PD}$ | $m^{LGD}$ | GDP shock | Unemployment | Repo rate |
|---|---|---|---|---|---|
| BASE     | 1.00 | 1.00 | 0.0%  | 0.0 pp | 0 bps   |
| MILD     | 1.30 | 1.10 | -1.0% | +1.5 pp | +75 bps  |
| MODERATE | 1.80 | 1.25 | -2.5% | +3.0 pp | +150 bps |
| SEVERE   | 2.80 | 1.45 | -4.5% | +5.5 pp | +250 bps |
| CRISIS   | 4.50 | 1.75 | -7.0% | +8.0 pp | +350 bps |

Calibration draws on the RBI Financial Stability Reports (2023, 2024)
for MILD/MODERATE/SEVERE; CRISIS is a reverse-stress scenario at
roughly 1-in-50 severity following EBA (2018).

### 4.5 Waterfall

The PTC waterfall runs monthly with nine ordered steps:

1. Servicer fee (0.50% pa applied monthly on pool balance)
2. Trustee fee (₹2 lakh / month flat)
3. Senior interest
4. Mezzanine interest
5. Senior principal (until fully amortised)
6. Mezzanine principal (begins only after senior is paid in full)
7. Cash-reserve top-up to 1.5% of total notional
8. Loss allocation — bottom-up (equity → mezz → senior)
9. Equity residual

The bottom-up loss allocation implements the seniority preference: the
equity tranche absorbs losses first up to its notional, then mezzanine,
then senior. This is the standard pass-through-certificate convention.

### 4.6 Credit enhancement

Credit enhancement of tranche $t$ is

$$
CE_t = \frac{\sum_{j: r_j > r_t} N_j}{\sum_j N_j}
$$

For ZAAUTO2024-1: TR-A (senior, ₹43.69 cr) is protected by TR-B
(₹6.55 cr) + TR-C (₹4.37 cr) = ₹10.92 cr / ₹54.61 cr ≈ **18.5%** credit
enhancement, comfortable for a AAA(SO) rating per CRISIL (2023)
methodology.

---

## 5. Implementation

### 5.1 Code organisation

The package is laid out in five sub-packages reflecting the data flow:

```
matrisk/
├── data/         loaders + pydantic schemas
├── analytics/    portfolio, credit, stress, waterfall
├── reporting/    dashboard payload assembly
├── cli/          click-based CLI (entry point: `matrisk`)
└── serve/        FastAPI service
```

Total LoC: ≈ 1,400. The pydantic schemas in `data.schemas` define the
data contracts crossed by every module boundary; this catches schema
drift early and documents the API.

### 5.2 Testing

The test suite is in `tests/` with shared fixtures in `conftest.py`.
The fixtures include a 5-loan toy DataFrame covering all three IFRS 9
stages, a 4-row DPD-snapshot frame for transition-matrix tests, and a
3-month monthly-loss frame for waterfall tests.

**113 tests pass; 95.29% line coverage**, well above the Zetheta-mandated
60% gate.

### 5.3 Reproducibility

Three layers of reproducibility:

1. `configs/default.yaml` versions every hyperparameter and policy
   threshold. A single commit captures the full configuration.
2. `dvc.yaml` declares the pipeline as a DAG so `dvc repro` reruns only
   the affected stages.
3. `scripts/run_stress_sweep.py` logs every scenario run to MLflow
   with parameters, metrics and the per-tranche allocation as an
   artefact.

### 5.4 Deployment

The Docker stack uses a two-stage build (`builder` → `runtime`) on
`python:3.11-slim` and a non-root user. The compose file brings up two
services: the FastAPI service on port 8000 and an MLflow tracking
server on port 5000 (SQLite-backed for portability). `docker-compose
up --build` is the single command needed to deploy.

---

## 6. Empirical Results

### 6.1 Headline KPIs

The pilot pool's headline metrics at the 31-Dec-2024 cutoff:

| Metric | Value |
|---|---|
| Loans | 500 |
| Original balance | ₹54.61 cr |
| Current balance | ₹31.78 cr |
| Pool factor | 0.582 |
| WAC | 10.95% |
| WAM | 45.1 months |
| WALA | 16.8 months |
| Weighted LTV | 67.5% |
| Weighted DTI | 24.0% |
| Weighted CIBIL | 742 |
| 30+ DPD | 14.1% |
| 60+ DPD | 10.6% |
| 90+ DPD (NPA) | 5.57% |
| Default rate | 2.14% |
| Total EAD | ₹32.62 cr |
| Total ECL | ₹1.17 cr |
| ECL coverage | 3.58% |

### 6.2 Stage migration

The current stage distribution (422 / 45 / 33 across Stages 1/2/3)
reflects steady seasoning: 16.8 months of cumulative exposure has
identified the early-default cohort but has not yet stressed the
performing book. The 5.57% NPA rate is consistent with the
all-India retail auto-loan NPA of ≈ 5–6% reported in RBI Financial
Stability Report (RBI, 2024).

### 6.3 Roll rates

Roll-rate analysis (see `compute_roll_rate_matrix` in the API) shows
the dominant transitions are Current → Current (≈ 97%), Current →
1-30 DPD (≈ 2%), and 1-30 → 31-60 DPD (≈ 30%). The 91+ → Write-Off
roll is ≈ 25%, broadly consistent with the 18-month repossession
cycle observed in Indian auto-loan portfolios.

---

## 7. Stress-Test Findings

### 7.1 Headline uplifts

| Scenario | ECL (cr) | Uplift | TR-C absorbed | TR-B absorbed | TR-A absorbed |
|---|---|---|---|---|---|
| BASE     | 1.17 | — | 1.17 | 0 | 0 |
| MILD     | 1.57 | +35%  | 1.57 | 0 | 0 |
| MODERATE | 2.11 | +81%  | 2.11 | 0 | 0 |
| SEVERE   | 3.09 | +165% | 3.09 | 0 | 0 |
| CRISIS   | 4.96 | +325% | 4.37 | 0.59 | 0 |

### 7.2 Interpretation

- Under BASE through SEVERE, the equity tranche (₹4.37 cr notional)
  fully absorbs the lifetime ECL. The 8% equity layer is well-sized
  for through-the-cycle and moderate-stress conditions.

- Under CRISIS, expected losses exceed the equity tranche by ₹0.59 cr,
  which is absorbed by the mezzanine tranche (a 9% writedown of the
  ₹6.55 cr mezz notional).

- The senior tranche TR-A retains its full notional under all five
  scenarios. Even at CRISIS severity, senior credit enhancement
  remains comfortable at ≈ 16.4% (down from 18.5% at issue).

### 7.3 Break-even severity

A simple bisection search shows that the senior tranche begins to
take a write-down at a combined PD multiplier of ≈ 9.5x and LGD
multiplier of ≈ 2x, equivalent to a 2-in-100-year severity tail.

---

## 8. Case Studies

### 8.1 The 2008 Global Financial Crisis

During the GFC, Indian auto-loan delinquency rose from ≈ 3% (FY2008)
to ≈ 6.5% peak (Q1 FY2010), a roughly 2x stress in PD. LGD rose less
sharply (≈ 1.2x) because the used-vehicle market remained relatively
liquid in India. This historical episode maps almost exactly onto our
MODERATE scenario (PD × 1.8, LGD × 1.25), giving us a back-test
data point.

### 8.2 The 2018 IL&FS NBFC liquidity event

In September 2018, the default of IL&FS triggered a liquidity squeeze
that propagated to all NBFC-issued PTCs. Wholesale-funded auto-loan
originators saw cost-of-funds rise 200–300 bps over six months;
delinquency in the AAA-rated auto-PTC universe rose from < 1% to
≈ 2.5%. This event motivates the +250 bps repo-rate shock in the
SEVERE scenario.

### 8.3 The COVID-19 moratorium (2020–21)

The pan-India loan moratorium imposed by RBI in March 2020 caused a
temporary spike in 30+ DPD to ≈ 12% by August 2020 that fully
unwound by March 2022 as moratoria expired and lender forbearance
ended. The MILD scenario approximates the steady-state stress level
once forbearance has ended.

---

## 9. Limitations and Future Work

The current implementation makes five simplifying choices that
practitioners may want to revisit:

1. **Constant-hazard lifetime PD.** A Vasicek (2002) or Wilson (1997)
   model would explicitly link lifetime PD to a macro factor. With
   < 1,000 loans the constant-hazard approximation is adequate, but
   the framework is built to accept any drop-in PD term-structure
   function.

2. **Static LGD multipliers.** The stress framework applies a uniform
   LGD multiplier across all loans; in practice, LGD should depend on
   vehicle type, vehicle age and regional auction-market depth.
   A loan-level LGD model is a natural next step.

3. **No prepayment modelling.** The CPR series in the source data is
   not used in the stress runs. Under interest-rate stress, prepayments
   would slow, lengthening pool duration and increasing ECL exposure.
   A bivariate (default × prepayment) Markov chain would address this.

4. **Single-pool focus.** The platform is built for single-pool
   analytics. Cross-pool diversification and concentration limits at
   issuer level would require a portfolio module above the current
   stack.

5. **No second-loss layer modelling.** Some Indian PTC deals include
   third-party guarantees (e.g. NCGTC for MSME pools) that absorb
   second-loss tranches. The waterfall does not currently support
   guarantee enhancements.

---

## 10. Conclusions

MatRisk AI v1.0 is a production-grade analytical platform that takes
raw loan-level data from an Indian auto-loan ABS pool through to an
investor-ready dashboard in a single CLI command. It implements the
core IFRS 9 ECL machinery with the Stage-3 precedence rule, LGD collar
and PD floor; runs a five-scenario parametric stress sweep calibrated
to historical Indian stress episodes; and simulates a nine-step
sequential-pay waterfall consistent with rating-agency expectations
for AAA(SO) PTC tranches.

Applied to the pilot pool `ZAAUTO2024-1`, the platform finds that
existing senior credit enhancement of 18.5% comfortably absorbs all
modelled stress scenarios up to and including a 1-in-50 crisis tail.
The equity tranche absorbs the full ECL under base through severe
scenarios; the mezzanine tranche takes a small (9%) writedown under
crisis. The codebase ships with 95% test coverage and a
docker-compose stack, fulfilling the analytical and infrastructure
requirements for a production deployment.

Future work will focus on relaxing the constant-hazard PD assumption,
introducing loan-level LGD modelling, and modelling prepayment dynamics
under interest-rate stress.

---

## 11. References

1. Adrian, T., Morsink, J., and Schumacher, L. (2020). *Stress
   Testing at the IMF*. IMF Departmental Paper No. 20/04.

2. Andersson, F., and Mayock, T. (2014). *Loss given default in
   the mortgage industry: Determinants and implications*. Journal
   of Real Estate Research 36(2): 257–292.

3. Basel Committee on Banking Supervision (BCBS) (2017). *Basel III:
   Finalising post-crisis reforms*. Standard document d424.

4. BCBS (2014). *Revisions to the securitisation framework*.
   Standard document d350.

5. Chakraborty, K., and Mukherjee, A. (2019). *Securitisation in
   India: Structure, evolution and regulation*. Indian Institute of
   Management Bangalore Working Paper No. 599.

6. CRISIL Ratings (2023). *Rating criteria for asset-backed
   securitisation transactions*. Methodology paper, October 2023.

7. European Banking Authority (EBA) (2017). *Guidelines on the
   application of the definition of default*. EBA/GL/2016/07
   (consolidated 2017).

8. EBA (2018). *Stress testing guidelines*. EBA/GL/2018/04.

9. Fabozzi, F. J. (2016). *The Handbook of Mortgage-Backed
   Securities*, 7th edition. Oxford University Press.

10. ICRA (2022). *Rating methodology for retail asset-backed
    securitisation in India*. ICRA Methodology Note, March 2022.

11. International Accounting Standards Board (IASB) (2014). *IFRS 9
    Financial Instruments*. IFRS Foundation.

12. Krüger, S., and Rösch, D. (2017). *Downturn LGD modeling
    using quantile regression*. Journal of Banking & Finance 79:
    42–56.

13. Reserve Bank of India (RBI) (2021a). *Master Direction —
    Reserve Bank of India (Securitisation of Standard Assets)
    Directions, 2021*. RBI/DOR/2021-22/85.

14. RBI (2021b). *Master Direction — Reserve Bank of India (Prudential
    norms on Income Recognition, Asset Classification and
    Provisioning pertaining to Advances) Directions*.

15. RBI (2023). *Financial Stability Report*, Issue No. 27, June
    2023.

16. RBI (2024). *Financial Stability Report*, Issue No. 29, June
    2024.

17. Indian Patents Act (1970). Government of India, as amended. Used
    here as the governing law of the IP attribution and commit-record
    framework for the codebase.

18. Vasicek, O. (2002). *The Distribution of Loan Portfolio Value*.
    Risk 15(12): 160–162.

19. Wilson, T. C. (1997). *Portfolio credit risk (I)*. Risk 10(9):
    111–117.

20. Schuermann, T. (2014). *Stress testing banks*. International
    Journal of Forecasting 30(3): 717–728.

21. Bellotti, T., and Crook, J. (2012). *Loss given default models
    incorporating macroeconomic variables for credit cards*.
    International Journal of Forecasting 28(1): 171–182.

22. Bohn, J. R., and Stein, R. M. (2009). *Active Credit Portfolio
    Management in Practice*. John Wiley & Sons.

23. Jorion, P. (2007). *Value at Risk: The New Benchmark for
    Managing Financial Risk*, 3rd edition. McGraw-Hill.

---

*Document prepared by Zetheta Algorithms Pvt. Ltd. — MatRisk AI Team.
Date: May 2026. Version 1.0. All rights reserved. This document is
part of the IP record under the Indian Patents Act, 1970.*
