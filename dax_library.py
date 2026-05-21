
from __future__ import annotations

import argparse
import json
import logging
import re
import sys
import textwrap
from collections import Counter
from dataclasses import dataclass, field
from enum import Enum
from pathlib import Path
from typing import Iterable, Iterator

logger = logging.getLogger(__name__)


class Category(str, Enum):
    """The 17 analytical domains plus two auxiliary buckets.

    String-valued so the enum members serialise cleanly into the .dax
    section banners and the markdown / TMSL exports.
    """

    CALENDAR = "01. Calendar & Date Helpers"
    PORTFOLIO_CORE = "02. Portfolio Core"
    WEIGHTED_AVG = "03. Weighted Averages"
    DELINQUENCY = "04. Delinquency & DPD Buckets"
    DEFAULT_LOSS = "05. Default & Loss"
    RECOVERY = "06. Recovery"
    PREPAYMENT = "07. Prepayment (SMM, CPR)"
    IFRS9 = "08. IFRS 9 Staging & ECL"
    STRESS = "09. Stress Testing"
    TRANCHE = "10. Tranche & Waterfall"
    INVESTOR = "11. Investor Reporting"
    COLLECTION = "12. Collection Efficiency & Ops"
    VINTAGE = "13. Vintage / Static Pool"
    ROLL_RATE = "14. Roll-Rate & Transition"
    TIME_INTEL = "15. Time Intelligence"
    RANKING = "16. Ranking & Dynamic"
    RAROC = "17. Risk-Adjusted Returns & Yield"
    # Auxiliary buckets — visual / presentation layer rather than analytics.
    HEATMAP = "Aux. Heat-Map Conditional Formatting"
    KPI_HEADLINE = "Aux. Dynamic KPI Headlines"

class Fmt:
    """Named format-string constants reused across measures."""

    INR = "\"₹\"#,0;(\"₹\"#,0)"           # rupees with parentheses for negatives
    INR_CR = "\"₹\"#,0.00,,\" Cr\""       # rupees in crores
    INR_LAKH = "\"₹\"#,0.00,\" L\""        # rupees in lakhs
    PCT_1 = "0.0%"                         # one-decimal percent
    PCT_2 = "0.00%"                        # two-decimal percent
    PCT_3 = "0.000%"                       # three-decimal percent
    INT = "#,##0"                          # integer with thousands separators
    DEC_2 = "0.00"                         # plain two-decimal number
    DEC_4 = "0.0000"                       # four-decimal (pool factor, etc.)
    MONTHS = "0.0\" m\""                   # months suffix
    SCORE = "0"                            # CIBIL score, etc.
    TEXT = ""                              # textual measure (no format)

_MEASURE_REF_RE = re.compile(r"(?<![A-Za-z0-9_])\[([^\]]+)\]")


@dataclass(frozen=True, slots=True)
class DaxMeasure:
    """A single DAX measure.

    Attributes
    ----------
    name
        Display name as it appears between square brackets in DAX
        (e.g. ``"Total ECL"``).  Must be unique within the library.
    expression
        The raw DAX expression — everything to the right of ``=`` in
        the canonical .dax file.  Multi-line expressions are accepted
        and re-indented on emit.
    category
        Section the measure belongs to.  Drives ordering in the .dax
        file and grouping in the markdown export.
    format_string
        Power BI ``FORMAT_STRING`` model property.  Empty for text
        measures.
    description
        One-line summary used as a code comment above the expression
        in the .dax file and as the measure description in TMSL.
    """

    name: str
    expression: str
    category: Category
    format_string: str = ""
    description: str = ""

    def __post_init__(self) -> None:
        if not self.name.strip():
            raise ValueError("DAX measure name must be non-empty")
        if not self.expression.strip():
            raise ValueError(f"DAX measure {self.name!r} has empty expression")

    def referenced_measures(self) -> set[str]:
        """Return every other measure name referenced inside this expression."""
        return {m for m in _MEASURE_REF_RE.findall(self.expression) if m != self.name}

    def to_dax_block(self) -> str:
        """Emit this measure as it would appear in the .dax file."""
        body = textwrap.dedent(self.expression).strip("\n")
        head = f"[{self.name}] =\n    "
        # Indent every body line by 4 spaces beyond the assignment.
        indented = body.replace("\n", "\n    ")
        prefix = f"// {self.description}\n" if self.description else ""
        return f"{prefix}{head}{indented}\n"

    def to_tmsl_dict(self) -> dict:
        """Emit a TMSL measure object suitable for Tabular Model JSON."""
        out: dict = {"name": self.name, "expression": self.expression.strip()}
        if self.format_string:
            out["formatString"] = self.format_string
        if self.description:
            out["description"] = self.description
        return out

@dataclass
class DaxMeasureLibrary:
    """Ordered collection of all DAX measures for the model.

    The class is iterable and indexable by name; ``len()`` returns the
    measure count.  Validation can be triggered manually via
    :meth:`validate` or implicitly by calling :meth:`to_dax_text`.
    """

    pool_id: str = "ZAAUTO2024-1"
    measures: list[DaxMeasure] = field(default_factory=list)

    def __iter__(self) -> Iterator[DaxMeasure]:
        return iter(self.measures)

    def __len__(self) -> int:
        return len(self.measures)

    def __getitem__(self, name: str) -> DaxMeasure:
        for m in self.measures:
            if m.name == name:
                return m
        raise KeyError(f"No DAX measure named {name!r}")

    def names(self) -> list[str]:
        """All measure names in insertion order."""
        return [m.name for m in self.measures]

    def by_category(self, category: Category) -> list[DaxMeasure]:
        """Measures filtered to one analytical domain."""
        return [m for m in self.measures if m.category is category]

    def category_counts(self) -> dict[Category, int]:
        """Histogram of measures per category."""
        c = Counter(m.category for m in self.measures)
        return {cat: c.get(cat, 0) for cat in Category}

    def validate(self) -> list[str]:
        """Return a list of validation issues (empty list = library is healthy)."""
        issues: list[str] = []

        # Uniqueness
        seen = Counter(m.name for m in self.measures)
        dupes = [n for n, c in seen.items() if c > 1]
        if dupes:
            issues.append(f"Duplicate measure names: {sorted(dupes)!r}")

        # Internal reference integrity
        known = set(self.names())
        # Known DAX functions / TMSL keywords that look like [Bracket]
        # references when they appear inside the regex match — none currently,
        # but reserved for future extension.
        whitelist: set[str] = set()
        for m in self.measures:
            unknown = m.referenced_measures() - known - whitelist
            for ref in sorted(unknown):
                issues.append(f"Measure {m.name!r} references unknown measure [{ref}]")
        return issues

    def to_dax_text(self) -> str:
        """Render the entire library as the canonical .dax file content."""
        issues = self.validate()
        if issues:
            for i in issues:
                logger.warning("DAX validation: %s", i)

        lines: list[str] = []
        lines.append(
            "// =========================================================================="
        )
        lines.append(
            "// DAX MEASURE LIBRARY — Zenith Securitisation Risk Analytics"
        )
        lines.append(
            f"// Pool: {self.pool_id} | Engine: Power BI VertiPaq"
        )
        lines.append(
            "// Generated from matrisk.reporting.dax_library — do not hand-edit"
        )
        lines.append(
            "// =========================================================================="
        )
        lines.append("")

        # Group by category, preserving Category enum order.
        for cat in Category:
            block = self.by_category(cat)
            if not block:
                continue
            lines.append(
                "// ====================================================================="
            )
            lines.append(f"// {cat.value}")
            lines.append(
                "// ====================================================================="
            )
            lines.append("")
            for m in block:
                lines.append(m.to_dax_block())

        lines.append("// ==========================================================================")
        lines.append(f"// END — {len(self.measures)} measures across {sum(1 for c in Category if self.by_category(c))} domains")
        lines.append("// ==========================================================================")
        return "\n".join(lines) + "\n"

    def to_tmsl(self, table_name: str = "fact_loan") -> dict:
        """Emit a minimal TMSL fragment with all measures attached to a table.

        The returned dict is the ``measures`` array body — it can be merged
        into a full TMSL model by the consumer.
        """
        return {
            "table": table_name,
            "measures": [m.to_tmsl_dict() for m in self.measures],
        }

    def to_markdown(self) -> str:
        """Documentation-friendly markdown table grouped by category."""
        lines = ["# MatRisk AI · DAX Measure Library", ""]
        lines.append(f"**Pool:** `{self.pool_id}`  ")
        lines.append(f"**Measure count:** {len(self.measures)}  ")
        lines.append("")
        for cat in Category:
            block = self.by_category(cat)
            if not block:
                continue
            lines.append(f"## {cat.value}")
            lines.append("")
            lines.append("| Measure | Format | Description |")
            lines.append("|---|---|---|")
            for m in block:
                fmt = m.format_string or "—"
                desc = m.description.replace("|", "\\|") if m.description else ""
                lines.append(f"| `[{m.name}]` | `{fmt}` | {desc} |")
            lines.append("")
        return "\n".join(lines)

    def write_dax(self, path: str | Path) -> Path:
        """Render and write the canonical .dax file."""
        p = Path(path)
        p.parent.mkdir(parents=True, exist_ok=True)
        p.write_text(self.to_dax_text(), encoding="utf-8")
        logger.info("Wrote DAX library (%d measures) to %s", len(self.measures), p)
        return p

    def write_tmsl(self, path: str | Path, table_name: str = "fact_loan") -> Path:
        """Render and write a TMSL JSON fragment."""
        p = Path(path)
        p.parent.mkdir(parents=True, exist_ok=True)
        p.write_text(
            json.dumps(self.to_tmsl(table_name=table_name), indent=2), encoding="utf-8"
        )
        logger.info("Wrote TMSL JSON to %s", p)
        return p


def _m(
    measures: list[DaxMeasure],
    name: str,
    expression: str,
    category: Category,
    *,
    fmt: str = "",
    desc: str = "",
) -> None:
    """Append a DaxMeasure to ``measures`` — keeps the registry below short."""
    measures.append(
        DaxMeasure(
            name=name,
            expression=textwrap.dedent(expression).strip(),
            category=category,
            format_string=fmt,
            description=desc,
        )
    )


def build_library(pool_id: str = "ZAAUTO2024-1") -> DaxMeasureLibrary:
    """Construct the canonical :class:`DaxMeasureLibrary` for MatRisk AI."""
    ms: list[DaxMeasure] = []
    _m(
        ms,
        "Latest Snapshot Date",
        "CALCULATE ( MAX ( fact_dpd_snapshot[SnapshotDate] ), ALL ( fact_dpd_snapshot ) )",
        Category.CALENDAR,
        desc="Most recent snapshot date present in the DPD snapshot table.",
    )
    _m(
        ms,
        "Latest Reporting Date",
        "CALCULATE ( MAX ( fact_loss_monthly[ReportingDate] ), ALL ( fact_loss_monthly ) )",
        Category.CALENDAR,
        desc="Most recent reporting date present in the monthly loss table.",
    )
    _m(
        ms,
        "Selected Period Label",
        """
        VAR _d = SELECTEDVALUE ( dim_calendar[Date], [Latest Reporting Date] )
        RETURN FORMAT ( _d, "MMM-YYYY" )
        """,
        Category.CALENDAR,
        fmt=Fmt.TEXT,
        desc="Human-readable label for the currently selected period.",
    )

    _m(ms, "Loan Count", "DISTINCTCOUNT ( fact_loan[LoanID] )", Category.PORTFOLIO_CORE, fmt=Fmt.INT)
    _m(ms, "Borrower Count", "DISTINCTCOUNT ( fact_loan[BorrowerID] )", Category.PORTFOLIO_CORE, fmt=Fmt.INT)
    _m(ms, "Original Pool Balance", "SUM ( fact_loan[OriginalLoanAmount] )", Category.PORTFOLIO_CORE, fmt=Fmt.INR)
    _m(ms, "Current Pool Balance", "SUM ( fact_loan[CurrentBalance] )", Category.PORTFOLIO_CORE, fmt=Fmt.INR)
    _m(ms, "Total EAD", "SUM ( fact_loan[EAD] )", Category.PORTFOLIO_CORE, fmt=Fmt.INR)
    _m(
        ms,
        "Pool Factor",
        "DIVIDE ( [Current Pool Balance], [Original Pool Balance] )",
        Category.PORTFOLIO_CORE,
        fmt=Fmt.DEC_4,
        desc="Current outstanding ÷ original — pool amortisation indicator.",
    )
    _m(ms, "Avg Loan Size", "DIVIDE ( [Current Pool Balance], [Loan Count] )", Category.PORTFOLIO_CORE, fmt=Fmt.INR)
    _m(ms, "Avg Original Term Months", "AVERAGE ( fact_loan[OriginalTerm] )", Category.PORTFOLIO_CORE, fmt=Fmt.MONTHS)
    _m(ms, "Avg Months on Book", "AVERAGE ( fact_loan[MonthsOnBook] )", Category.PORTFOLIO_CORE, fmt=Fmt.MONTHS)
    _m(
        ms,
        "Pool Balance at Snapshot",
        """
        CALCULATE (
            SUM ( fact_dpd_snapshot[CurrentBalance] ),
            fact_dpd_snapshot[SnapshotDate] = [Latest Snapshot Date]
        )
        """,
        Category.PORTFOLIO_CORE,
        fmt=Fmt.INR,
        desc="Sum of current balance across loans at the latest snapshot.",
    )

    for nm, col, fmt_, descr in [
        ("WAC %",            "InterestRate",       Fmt.PCT_2, "Weighted average coupon (balance-weighted)."),
        ("WAM Months",       "RemainingTerm",      Fmt.MONTHS, "Weighted average remaining maturity (months)."),
        ("WALA Months",      "MonthsOnBook",       Fmt.MONTHS, "Weighted average loan age (months on book)."),
        ("Weighted Avg LTV %",  "LTV_Current",     Fmt.PCT_2, "Balance-weighted current LTV ratio."),
        ("Weighted Avg DTI %",  "DTI_Ratio",       Fmt.PCT_2, "Balance-weighted debt-to-income."),
        ("Weighted Avg CIBIL",  "CIBIL_Score_Current", Fmt.SCORE, "Balance-weighted CIBIL score."),
    ]:
        _m(
            ms,
            nm,
            f"""
            DIVIDE (
                SUMX ( fact_loan, fact_loan[{col}] * fact_loan[CurrentBalance] ),
                SUMX ( fact_loan, fact_loan[CurrentBalance] )
            )
            """,
            Category.WEIGHTED_AVG,
            fmt=fmt_,
            desc=descr,
        )
    _m(
        ms,
        "Portfolio Yield %",
        "[WAC %]",
        Category.WEIGHTED_AVG,
        fmt=Fmt.PCT_2,
        desc="Gross asset yield (alias for WAC); net yield deducts servicer + trustee fees.",
    )

    for threshold in (30, 60, 90):
        _m(
            ms,
            f"Loans {threshold}+ DPD Count",
            f"CALCULATE ( [Loan Count], fact_loan[DelinquencyDays] >= {threshold} )",
            Category.DELINQUENCY,
            fmt=Fmt.INT,
        )
        _m(
            ms,
            f"Balance {threshold}+ DPD",
            f"CALCULATE ( [Current Pool Balance], fact_loan[DelinquencyDays] >= {threshold} )",
            Category.DELINQUENCY,
            fmt=Fmt.INR,
        )
        _m(
            ms,
            f"{threshold}+ DPD %",
            f"DIVIDE ( [Balance {threshold}+ DPD], [Current Pool Balance] )",
            Category.DELINQUENCY,
            fmt=Fmt.PCT_2,
        )
    _m(
        ms,
        "Delinquency Rate %",
        "DIVIDE ( [Loans 30+ DPD Count], [Loan Count] )",
        Category.DELINQUENCY,
        fmt=Fmt.PCT_2,
        desc="Share of loans that are 30+ days past due (loan count basis).",
    )
    _m(
        ms,
        "NPA Balance",
        """
        CALCULATE (
            SUM ( fact_dpd_snapshot[CurrentBalance] ),
            fact_dpd_snapshot[SnapshotDate] = [Latest Snapshot Date],
            fact_dpd_snapshot[RBI_SMA_Class] = "NPA"
        )
        """,
        Category.DELINQUENCY,
        fmt=Fmt.INR,
        desc="Non-performing balance per RBI classification at latest snapshot.",
    )
    _m(ms, "NPA %", "DIVIDE ( [NPA Balance], [Pool Balance at Snapshot] )", Category.DELINQUENCY, fmt=Fmt.PCT_2)
    _m(ms, "GNPA Ratio %", "[NPA %]", Category.DELINQUENCY, fmt=Fmt.PCT_2,
       desc="Gross NPA ratio — alias of NPA % retained for regulatory cross-referencing.")
    _m(
        ms,
        "Net NPA Balance",
        """
        VAR _gnpa = [NPA Balance]
        VAR _provns =
            CALCULATE ( SUM ( fact_loan[ECL_Provision] ), fact_loan[IFRS9_Stage] = 3 )
        RETURN MAX ( _gnpa - _provns, 0 )
        """,
        Category.DELINQUENCY,
        fmt=Fmt.INR,
        desc="NPA balance net of Stage-3 ECL provisions (floored at zero).",
    )
    _m(ms, "Net NPA %", "DIVIDE ( [Net NPA Balance], [Pool Balance at Snapshot] )",
       Category.DELINQUENCY, fmt=Fmt.PCT_2)

    _m(ms, "Defaulted Loan Count", "CALCULATE ( [Loan Count], fact_loan[IsDefaulted] = TRUE() )",
       Category.DEFAULT_LOSS, fmt=Fmt.INT)
    _m(ms, "Default Rate %", "DIVIDE ( [Defaulted Loan Count], [Loan Count] )",
       Category.DEFAULT_LOSS, fmt=Fmt.PCT_2)
    _m(ms, "Total Gross Loss", "SUM ( fact_loan[LossAmount] )", Category.DEFAULT_LOSS, fmt=Fmt.INR)
    _m(ms, "Total Net Loss", "SUM ( fact_loan[NetLoss] )", Category.DEFAULT_LOSS, fmt=Fmt.INR)
    _m(ms, "Gross Loss Rate %", "DIVIDE ( [Total Gross Loss], [Original Pool Balance] )",
       Category.DEFAULT_LOSS, fmt=Fmt.PCT_2)
    _m(ms, "Net Loss Rate %", "DIVIDE ( [Total Net Loss], [Original Pool Balance] )",
       Category.DEFAULT_LOSS, fmt=Fmt.PCT_2)
    _m(ms, "Monthly Default Rate %", "AVERAGE ( fact_loss_monthly[MonthlyDefaultRate] )",
       Category.DEFAULT_LOSS, fmt=Fmt.PCT_3)
    _m(
        ms,
        "CDR Annualised %",
        """
        VAR _mdr = AVERAGE ( fact_loss_monthly[MonthlyDefaultRate] )
        RETURN 1 - POWER ( 1 - _mdr, 12 )
        """,
        Category.DEFAULT_LOSS,
        fmt=Fmt.PCT_2,
        desc="Annualised constant default rate: 1 − (1 − MDR)^12.",
    )

    _m(ms, "Total Recovery", "SUM ( fact_loan[RecoveryAmount] )", Category.RECOVERY, fmt=Fmt.INR)
    _m(ms, "Recovery Rate %", "DIVIDE ( [Total Recovery], [Total Gross Loss] )",
       Category.RECOVERY, fmt=Fmt.PCT_2)
    _m(ms, "Monthly Recovery", "SUM ( fact_loss_monthly[Recoveries_ThisMonth] )",
       Category.RECOVERY, fmt=Fmt.INR)

    _m(ms, "Total Prepayment", "SUM ( fact_loan[PrepaymentAmount] )", Category.PREPAYMENT, fmt=Fmt.INR)
    _m(ms, "Prepayment Rate %", "DIVIDE ( [Total Prepayment], [Original Pool Balance] )",
       Category.PREPAYMENT, fmt=Fmt.PCT_2)
    _m(ms, "SMM Avg %", "AVERAGE ( fact_loss_monthly[SMM] )", Category.PREPAYMENT, fmt=Fmt.PCT_3,
       desc="Single Monthly Mortality — share of EOP balance prepaid per month.")
    _m(ms, "CPR Annualised %", "AVERAGE ( fact_loss_monthly[CPR_Annualised] )",
       Category.PREPAYMENT, fmt=Fmt.PCT_2)
    _m(
        ms,
        "CPR Calc %",
        """
        VAR _smm = AVERAGE ( fact_loss_monthly[SMM] )
        RETURN 1 - POWER ( 1 - _smm, 12 )
        """,
        Category.PREPAYMENT,
        fmt=Fmt.PCT_2,
        desc="CPR derived from SMM as a cross-check on the reported CPR.",
    )
    for stage in (1, 2, 3):
        _m(ms, f"Stage {stage} Loan Count",
           f"CALCULATE ( [Loan Count], fact_loan[IFRS9_Stage] = {stage} )",
           Category.IFRS9, fmt=Fmt.INT)
        _m(ms, f"Stage {stage} Balance",
           f"CALCULATE ( [Current Pool Balance], fact_loan[IFRS9_Stage] = {stage} )",
           Category.IFRS9, fmt=Fmt.INR)
        _m(ms, f"Stage {stage} EAD",
           f"CALCULATE ( [Total EAD], fact_loan[IFRS9_Stage] = {stage} )",
           Category.IFRS9, fmt=Fmt.INR)
        _m(ms, f"Stage {stage} ECL",
           f"CALCULATE ( SUM ( fact_loan[ECL_Provision] ), fact_loan[IFRS9_Stage] = {stage} )",
           Category.IFRS9, fmt=Fmt.INR)

    _m(ms, "Total ECL", "SUM ( fact_loan[ECL_Provision] )", Category.IFRS9, fmt=Fmt.INR)
    _m(ms, "ECL Coverage %", "DIVIDE ( [Total ECL], [Total EAD] )",
       Category.IFRS9, fmt=Fmt.PCT_2,
       desc="Portfolio-level ECL ÷ EAD coverage.")
    _m(ms, "Stage 3 Coverage %", "DIVIDE ( [Stage 3 ECL], [Stage 3 EAD] )",
       Category.IFRS9, fmt=Fmt.PCT_2,
       desc="Stage-3 ECL as a share of Stage-3 EAD — impairment intensity.")
    _m(
        ms,
        "Weighted Avg PD %",
        """
        DIVIDE (
            SUMX ( fact_loan, fact_loan[PD_Estimate] * fact_loan[EAD] ),
            SUMX ( fact_loan, fact_loan[EAD] )
        )
        """,
        Category.IFRS9,
        fmt=Fmt.PCT_2,
        desc="EAD-weighted probability of default.",
    )
    _m(
        ms,
        "Weighted Avg LGD %",
        """
        DIVIDE (
            SUMX ( fact_loan, fact_loan[LGD_Estimate] * fact_loan[EAD] ),
            SUMX ( fact_loan, fact_loan[EAD] )
        )
        """,
        Category.IFRS9,
        fmt=Fmt.PCT_2,
        desc="EAD-weighted loss given default.",
    )
    _m(
        ms,
        "ECL Calculated",
        """
        SUMX (
            fact_loan,
            fact_loan[PD_Estimate] * fact_loan[LGD_Estimate] * fact_loan[EAD]
        )
        """,
        Category.IFRS9,
        fmt=Fmt.INR,
        desc="Validation: live PD × LGD × EAD vs. stored ECL_Provision.",
    )
    _m(
        ms,
        "Stage Migration Net %",
        """
        VAR _to_worse = CALCULATE ( [Loan Count], fact_loan[IFRS9_Stage] > 1 )
        RETURN DIVIDE ( _to_worse, [Loan Count] )
        """,
        Category.IFRS9,
        fmt=Fmt.PCT_2,
        desc="Share of loans not in Stage 1.",
    )
    _m(ms, "12-Month ECL", "CALCULATE ( SUM ( fact_loan[ECL_Provision] ), fact_loan[IFRS9_Stage] = 1 )",
       Category.IFRS9, fmt=Fmt.INR,
       desc="12-month ECL bucket per IFRS 9 §5.5.5 (Stage 1).")
    _m(ms, "Lifetime ECL",
       "CALCULATE ( SUM ( fact_loan[ECL_Provision] ), fact_loan[IFRS9_Stage] IN { 2, 3 } )",
       Category.IFRS9, fmt=Fmt.INR,
       desc="Lifetime ECL bucket per IFRS 9 §5.5.3 (Stages 2 & 3).")

    _m(ms, "Selected Scenario",
       "SELECTEDVALUE ( dim_scenario[ScenarioName], \"Baseline\" )",
       Category.STRESS, fmt=Fmt.TEXT)
    _m(ms, "Scenario PD Multiplier",
       "SELECTEDVALUE ( dim_scenario[PD_Multiplier], 1.0 )",
       Category.STRESS, fmt=Fmt.DEC_2)
    _m(ms, "Scenario LGD Multiplier",
       "SELECTEDVALUE ( dim_scenario[LGD_Multiplier], 1.0 )",
       Category.STRESS, fmt=Fmt.DEC_2)
    _m(ms, "Scenario Recovery Haircut %",
       "SELECTEDVALUE ( dim_scenario[Recovery_Haircut_Pct], 0 )",
       Category.STRESS, fmt=Fmt.PCT_2)
    _m(
        ms,
        "Stressed ECL",
        """
        VAR _pdm = [Scenario PD Multiplier]
        VAR _lgdm = [Scenario LGD Multiplier]
        VAR _haircut = [Scenario Recovery Haircut %]
        RETURN
            SUMX (
                fact_loan,
                MIN ( fact_loan[PD_Estimate] * _pdm, 1 ) *
                MIN ( fact_loan[LGD_Estimate] * _lgdm * ( 1 + _haircut ), 1 ) *
                fact_loan[EAD]
            )
        """,
        Category.STRESS,
        fmt=Fmt.INR,
        desc="Live-stressed ECL with PD & LGD caps at 100%.",
    )
    _m(ms, "ECL Increase from Stress", "[Stressed ECL] - [Total ECL]", Category.STRESS, fmt=Fmt.INR)
    _m(ms, "ECL Increase %", "DIVIDE ( [ECL Increase from Stress], [Total ECL] )",
       Category.STRESS, fmt=Fmt.PCT_2)
    _m(ms, "Stressed ECL by Stage", "SUM ( fact_stress_results[ECL_Stressed_INR] )",
       Category.STRESS, fmt=Fmt.INR)
    for trnch_id, label in [("TR-A", "Senior"), ("TR-B", "Mezz"), ("TR-C", "Equity")]:
        _m(
            ms,
            f"Stressed Loss to {label} Tranche",
            f"""
            CALCULATE (
                SUM ( fact_stress_results[ECL_Stressed_INR] ),
                fact_stress_results[Stage] = "{trnch_id}"
            )
            """,
            Category.STRESS,
            fmt=Fmt.INR,
            desc=f"Stressed loss absorbed by tranche {trnch_id} ({label}).",
        )

    # ------------------------------------------------------------------
    # 10. TRANCHE & WATERFALL
    # ------------------------------------------------------------------
    _m(ms, "Tranche Original Balance", "SUM ( dim_tranche[OriginalBalance_INR] )",
       Category.TRANCHE, fmt=Fmt.INR)
    _m(
        ms,
        "Tranche EOP Balance",
        """
        CALCULATE (
            SUM ( fact_tranche_cashflow[EOP_Balance] ),
            fact_tranche_cashflow[ReportingDate] = [Latest Reporting Date]
        )
        """,
        Category.TRANCHE,
        fmt=Fmt.INR,
    )
    _m(ms, "Tranche Paydown %",
       "DIVIDE ( [Tranche Original Balance] - [Tranche EOP Balance], [Tranche Original Balance] )",
       Category.TRANCHE, fmt=Fmt.PCT_2)
    _m(ms, "Cumulative Tranche Interest Paid", "SUM ( fact_tranche_cashflow[InterestPaid] )",
       Category.TRANCHE, fmt=Fmt.INR)
    _m(ms, "Cumulative Tranche Principal Paid", "SUM ( fact_tranche_cashflow[PrincipalPaid] )",
       Category.TRANCHE, fmt=Fmt.INR)
    _m(ms, "Cumulative Tranche Loss", "SUM ( fact_tranche_cashflow[LossAllocated] )",
       Category.TRANCHE, fmt=Fmt.INR)
    _m(
        ms,
        "Credit Enhancement %",
        """
        VAR _senior_bal =
            CALCULATE ( [Tranche EOP Balance], dim_tranche[TrancheID] = "TR-A" )
        VAR _total_bal =
            CALCULATE ( [Tranche EOP Balance], ALL ( dim_tranche ) )
        RETURN DIVIDE ( _total_bal - _senior_bal, _total_bal )
        """,
        Category.TRANCHE,
        fmt=Fmt.PCT_2,
        desc="Subordination remaining for the senior tranche.",
    )
    _m(ms, "Waterfall Amount", "SUM ( fact_waterfall_distribution[Amount] )",
       Category.TRANCHE, fmt=Fmt.INR)
    _m(ms, "Total Collections", "SUM ( fact_loss_monthly[CollectionsTotal] )",
       Category.TRANCHE, fmt=Fmt.INR)
    _m(ms, "Excess Spread", "SUM ( fact_loss_monthly[ExcessSpread_Monthly] )",
       Category.TRANCHE, fmt=Fmt.INR)
    _m(
        ms,
        "Cumulative Excess Spread",
        """
        CALCULATE (
            [Excess Spread],
            FILTER (
                ALL ( fact_loss_monthly ),
                fact_loss_monthly[ReportingDate] <= MAX ( fact_loss_monthly[ReportingDate] )
            )
        )
        """,
        Category.TRANCHE,
        fmt=Fmt.INR,
    )

    _m(ms, "Total Invested by Investors", "SUM ( dim_investor[InvestedAmount_INR] )",
       Category.INVESTOR, fmt=Fmt.INR)
    _m(ms, "Investor Count", "DISTINCTCOUNT ( dim_investor[InvestorID] )",
       Category.INVESTOR, fmt=Fmt.INT)
    for trnch_id, label in [("TR-A", "Senior"), ("TR-B", "Mezz"), ("TR-C", "Equity")]:
        _m(
            ms,
            f"{label} Investor Allocation",
            f"""
            CALCULATE (
                SUM ( dim_investor[InvestedAmount_INR] ),
                dim_investor[TrancheID] = "{trnch_id}"
            )
            """,
            Category.INVESTOR,
            fmt=Fmt.INR,
        )
    _m(
        ms,
        "FPI Allocation",
        """
        CALCULATE (
            SUM ( dim_investor[InvestedAmount_INR] ),
            dim_investor[InvestorType] = "Foreign Portfolio Investor"
        )
        """,
        Category.INVESTOR,
        fmt=Fmt.INR,
    )
    _m(ms, "FPI Allocation %", "DIVIDE ( [FPI Allocation], [Total Invested by Investors] )",
       Category.INVESTOR, fmt=Fmt.PCT_2)

    _m(
        ms,
        "Collection Efficiency %",
        """
        DIVIDE (
            SUM ( fact_loss_monthly[CollectionsTotal] ),
            SUM ( fact_loss_monthly[BillingAmount] )
        )
        """,
        Category.COLLECTION,
        fmt=Fmt.PCT_2,
    )
    _m(ms, "Avg Collection Efficiency %", "AVERAGE ( fact_loss_monthly[CollectionEfficiency] )",
       Category.COLLECTION, fmt=Fmt.PCT_2)
    _m(ms, "Avg Monthly Billing", "AVERAGE ( fact_loss_monthly[BillingAmount] )",
       Category.COLLECTION, fmt=Fmt.INR)
    _m(ms, "Cure Count",
       "CALCULATE ( COUNTROWS ( fact_dpd_snapshot ), fact_dpd_snapshot[CureFlag] = TRUE() )",
       Category.COLLECTION, fmt=Fmt.INT)
    _m(ms, "Repossession Count",
       "CALCULATE ( COUNTROWS ( fact_dpd_snapshot ), fact_dpd_snapshot[RepossessionFlag] = TRUE() )",
       Category.COLLECTION, fmt=Fmt.INT)
    _m(ms, "Write-Off Count",
       "CALCULATE ( COUNTROWS ( fact_dpd_snapshot ), fact_dpd_snapshot[WriteOffFlag] = TRUE() )",
       Category.COLLECTION, fmt=Fmt.INT)

    _m(ms, "Vintage Cumulative Net Loss %", "AVERAGE ( fact_vintage[CumulativeNetLossRate] )",
       Category.VINTAGE, fmt=Fmt.PCT_2)
    _m(
        ms,
        "Latest Vintage Net Loss %",
        """
        VAR _maxMOB =
            CALCULATE ( MAX ( fact_vintage[MonthsOnBook] ),
                        ALLEXCEPT ( fact_vintage, fact_vintage[VintageID] ) )
        RETURN
            CALCULATE (
                AVERAGE ( fact_vintage[CumulativeNetLossRate] ),
                fact_vintage[MonthsOnBook] = _maxMOB
            )
        """,
        Category.VINTAGE,
        fmt=Fmt.PCT_2,
    )
    _m(ms, "Vintage Pool Factor", "AVERAGE ( fact_vintage[PoolFactor] )",
       Category.VINTAGE, fmt=Fmt.DEC_4)
    _m(ms, "Vintage Marginal Loss Rate", "AVERAGE ( fact_vintage[MarginalLossRate] )",
       Category.VINTAGE, fmt=Fmt.PCT_3)
    for mob in (12, 24):
        _m(
            ms,
            f"Vintage Loss @ {mob} MOB",
            f"""
            CALCULATE (
                AVERAGE ( fact_vintage[CumulativeNetLossRate] ),
                fact_vintage[MonthsOnBook] = {mob}
            )
            """,
            Category.VINTAGE,
            fmt=Fmt.PCT_2,
            desc=f"Cumulative net loss at {mob} months on book.",
        )

    for flag, label in [("Forward Roll", "Loans Forward Rolled"),
                        ("Backward Roll", "Loans Backward Rolled"),
                        ("Same", "Loans Static")]:
        _m(
            ms,
            label,
            f"""
            CALCULATE (
                COUNTROWS ( fact_dpd_snapshot ),
                fact_dpd_snapshot[RollFlag] = "{flag}"
            )
            """,
            Category.ROLL_RATE,
            fmt=Fmt.INT,
        )
    _m(
        ms,
        "Forward Roll Rate %",
        """
        VAR _denom =
            CALCULATE (
                COUNTROWS ( fact_dpd_snapshot ),
                fact_dpd_snapshot[DPD_Bucket_Prior] <> "Current"
            )
        RETURN DIVIDE ( [Loans Forward Rolled], _denom )
        """,
        Category.ROLL_RATE,
        fmt=Fmt.PCT_2,
        desc="Forward rolls ÷ delinquent population at prior snapshot.",
    )
    _m(
        ms,
        "Cure Rate %",
        """
        DIVIDE (
            [Loans Backward Rolled],
            CALCULATE (
                COUNTROWS ( fact_dpd_snapshot ),
                fact_dpd_snapshot[DPD_Bucket_Prior] <> "Current"
            )
        )
        """,
        Category.ROLL_RATE,
        fmt=Fmt.PCT_2,
    )
    for from_bkt, to_bkt, lbl in [
        ("1-29 DPD", "30-59 DPD", "Roll 30 to 60 %"),
        ("30-59 DPD", "60-89 DPD", "Roll 60 to 90 %"),
    ]:
        _m(
            ms,
            lbl,
            f"""
            VAR _from =
                CALCULATE (
                    COUNTROWS ( fact_dpd_snapshot ),
                    fact_dpd_snapshot[DPD_Bucket_Prior] = "{from_bkt}"
                )
            VAR _to =
                CALCULATE (
                    COUNTROWS ( fact_dpd_snapshot ),
                    fact_dpd_snapshot[DPD_Bucket_Prior] = "{from_bkt}",
                    fact_dpd_snapshot[DPD_Bucket] = "{to_bkt}"
                )
            RETURN DIVIDE ( _to, _from )
            """,
            Category.ROLL_RATE,
            fmt=Fmt.PCT_2,
            desc=f"Transition probability {from_bkt} → {to_bkt}.",
        )
    _m(ms, "Net Loss MTD",
       "CALCULATE ( SUM ( fact_loss_monthly[NetLoss_ThisMonth] ), DATESMTD ( dim_calendar[Date] ) )",
       Category.TIME_INTEL, fmt=Fmt.INR)
    _m(ms, "Net Loss YTD",
       "CALCULATE ( SUM ( fact_loss_monthly[NetLoss_ThisMonth] ), DATESYTD ( dim_calendar[Date], \"31/03\" ) )",
       Category.TIME_INTEL, fmt=Fmt.INR,
       desc="Year-to-date net loss, Indian fiscal year (1 Apr – 31 Mar).")
    _m(ms, "Net Loss QTD",
       "CALCULATE ( SUM ( fact_loss_monthly[NetLoss_ThisMonth] ), DATESQTD ( dim_calendar[Date] ) )",
       Category.TIME_INTEL, fmt=Fmt.INR)
    _m(ms, "Pool Balance Prior Month",
       "CALCULATE ( [Current Pool Balance], DATEADD ( dim_calendar[Date], -1, MONTH ) )",
       Category.TIME_INTEL, fmt=Fmt.INR)
    _m(ms, "Pool Balance MoM Change %",
       "DIVIDE ( [Current Pool Balance] - [Pool Balance Prior Month], [Pool Balance Prior Month] )",
       Category.TIME_INTEL, fmt=Fmt.PCT_2)
    _m(
        ms,
        "Cumulative Net Loss",
        """
        CALCULATE (
            SUM ( fact_loss_monthly[NetLoss_ThisMonth] ),
            FILTER (
                ALL ( fact_loss_monthly[ReportingDate] ),
                fact_loss_monthly[ReportingDate] <= MAX ( fact_loss_monthly[ReportingDate] )
            )
        )
        """,
        Category.TIME_INTEL,
        fmt=Fmt.INR,
    )
    _m(
        ms,
        "Rolling 12M Default Rate %",
        """
        VAR _maxDate = MAX ( fact_loss_monthly[ReportingDate] )
        VAR _minDate = EDATE ( _maxDate, -11 )
        RETURN
            CALCULATE (
                AVERAGE ( fact_loss_monthly[MonthlyDefaultRate] ),
                FILTER (
                    ALL ( fact_loss_monthly ),
                    fact_loss_monthly[ReportingDate] >= _minDate &&
                    fact_loss_monthly[ReportingDate] <= _maxDate
                )
            )
        """,
        Category.TIME_INTEL,
        fmt=Fmt.PCT_3,
    )

    _m(
        ms,
        "State Rank by ECL",
        """
        RANKX (
            ALL ( dim_geography[State] ),
            [Total ECL],
            ,
            DESC,
            Dense
        )
        """,
        Category.RANKING,
        fmt=Fmt.INT,
    )
    _m(
        ms,
        "Top 5 Risky States ECL",
        """
        VAR _rank = [State Rank by ECL]
        RETURN IF ( _rank <= 5, [Total ECL], BLANK () )
        """,
        Category.RANKING,
        fmt=Fmt.INR,
    )
    _m(
        ms,
        "Servicer Rank by Balance",
        """
        RANKX (
            ALL ( dim_servicer[ServicerName] ),
            [Current Pool Balance],
            ,
            DESC,
            Dense
        )
        """,
        Category.RANKING,
        fmt=Fmt.INT,
    )
    _m(
        ms,
        "Top 10 Borrower Share %",
        """
        VAR _top10 =
            TOPN ( 10, VALUES ( fact_loan[BorrowerID] ), [Current Pool Balance], DESC )
        VAR _top10_bal =
            CALCULATE ( [Current Pool Balance], _top10 )
        RETURN DIVIDE ( _top10_bal, CALCULATE ( [Current Pool Balance], ALL ( fact_loan ) ) )
        """,
        Category.RANKING,
        fmt=Fmt.PCT_2,
        desc="Concentration ratio — top 10 borrower balance share.",
    )
    _m(
        ms,
        "Annualised Gross Interest Revenue",
        "SUMX ( fact_loan, fact_loan[CurrentBalance] * fact_loan[InterestRate] / 100 )",
        Category.RAROC,
        fmt=Fmt.INR,
    )
    _m(ms, "Expected Loss (Annual)", "[Total ECL]", Category.RAROC, fmt=Fmt.INR,
       desc="One-year EL approximation for RAROC denominator.")
    _m(
        ms,
        "Risk-Adjusted Return on Assets %",
        """
        DIVIDE (
            [Annualised Gross Interest Revenue] - [Expected Loss (Annual)],
            [Current Pool Balance]
        )
        """,
        Category.RAROC,
        fmt=Fmt.PCT_2,
    )
    _m(ms, "Tranche Coupon Revenue",
       "SUMX ( fact_tranche_cashflow, fact_tranche_cashflow[InterestPaid] )",
       Category.RAROC, fmt=Fmt.INR)
    _m(
        ms,
        "Tranche Yield Realised %",
        """
        DIVIDE (
            [Cumulative Tranche Interest Paid],
            AVERAGE ( fact_tranche_cashflow[BOP_Balance] )
        ) * 12
        """,
        Category.RAROC,
        fmt=Fmt.PCT_2,
    )

    _m(
        ms,
        "Heat 30+ DPD Colour",
        """
        SWITCH (
            TRUE (),
            [30+ DPD %] >= 0.10, "#C62828",
            [30+ DPD %] >= 0.06, "#EF6C00",
            [30+ DPD %] >= 0.03, "#F9A825",
            "#2E7D32"
        )
        """,
        Category.HEATMAP,
        fmt=Fmt.TEXT,
        desc="Conditional-format colour for the 30+ DPD KPI.",
    )
    _m(
        ms,
        "Heat Stage Mix Colour",
        """
        VAR _stg3 = DIVIDE ( [Stage 3 Balance], [Current Pool Balance] )
        RETURN
            SWITCH (
                TRUE (),
                _stg3 >= 0.10, "#C62828",
                _stg3 >= 0.05, "#EF6C00",
                _stg3 >= 0.02, "#F9A825",
                "#2E7D32"
            )
        """,
        Category.HEATMAP,
        fmt=Fmt.TEXT,
        desc="Conditional-format colour driven by Stage-3 balance share.",
    )

    _m(
        ms,
        "KPI Headline Risk Status",
        """
        SWITCH (
            TRUE (),
            [Stressed ECL] / [Total EAD] >= 0.10, "🔴 CRITICAL — Tail risk exposed",
            [Stressed ECL] / [Total EAD] >= 0.05, "🟠 ELEVATED — Active monitoring",
            [Stressed ECL] / [Total EAD] >= 0.02, "🟡 WATCH — Within tolerance",
            "🟢 HEALTHY — Within risk appetite"
        )
        """,
        Category.KPI_HEADLINE,
        fmt=Fmt.TEXT,
        desc="Traffic-light commentary card driven by stressed ECL coverage.",
    )

    return DaxMeasureLibrary(pool_id=pool_id, measures=ms)


LIBRARY: DaxMeasureLibrary = build_library()


DEFAULT_DAX_PATH = Path(__file__).resolve().parents[3] / "powerbi" / "dax" / "dax_measure_library.dax"


def _cli(argv: Iterable[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        description="MatRisk AI DAX measure library — generator and inspector.",
    )
    parser.add_argument(
        "--regen",
        action="store_true",
        help="Regenerate powerbi/dax/dax_measure_library.dax from this module.",
    )
    parser.add_argument(
        "--out",
        type=Path,
        default=DEFAULT_DAX_PATH,
        help="Output path when --regen is used (default: powerbi/dax/...).",
    )
    parser.add_argument(
        "--tmsl",
        type=Path,
        help="If provided, also emit a TMSL JSON fragment to this path.",
    )
    parser.add_argument(
        "--markdown",
        type=Path,
        help="If provided, emit a markdown documentation file to this path.",
    )
    parser.add_argument(
        "--stats", action="store_true", help="Print category counts and validation report."
    )
    args = parser.parse_args(list(argv) if argv is not None else None)

    logging.basicConfig(level=logging.INFO, format="%(levelname)s %(name)s %(message)s")

    lib = build_library()

    if args.stats:
        print(f"DAX library — pool {lib.pool_id} — {len(lib)} measures")
        for cat, n in lib.category_counts().items():
            if n:
                print(f"  {n:3d}  {cat.value}")
        issues = lib.validate()
        if issues:
            print(f"\n{len(issues)} validation issue(s):")
            for i in issues:
                print(f"  ✗ {i}")
            return 1
        print("\n✓ Library is internally consistent (all references resolve).")

    if args.regen:
        lib.write_dax(args.out)
        print(f"Wrote {args.out} ({len(lib)} measures)")
    if args.tmsl:
        lib.write_tmsl(args.tmsl)
        print(f"Wrote {args.tmsl}")
    if args.markdown:
        args.markdown.parent.mkdir(parents=True, exist_ok=True)
        args.markdown.write_text(lib.to_markdown(), encoding="utf-8")
        print(f"Wrote {args.markdown}")

    return 0


if __name__ == "__main__":
    sys.exit(_cli())
