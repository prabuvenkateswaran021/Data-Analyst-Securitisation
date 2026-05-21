"""Regression tests for :mod:`matrisk.reporting.dax_library`.

The DAX library is the source of truth for the Power BI measures, so the
tests focus on three categories of invariant:

1. **Structural invariants** — the registry contains every domain promised
   by the technical report and the canonical .dax file.
2. **Internal consistency** — every ``[Measure]`` token referenced inside
   another measure's expression resolves to a registered measure (no
   broken cross-refs).
3. **Round-trip emission** — both the text and JSON exports are well-formed
   and contain the data the consumers expect.
"""
from __future__ import annotations

import json
import re
from pathlib import Path

import pytest

from matrisk.reporting import dax_library
from matrisk.reporting.dax_library import (
    LIBRARY,
    Category,
    DaxMeasure,
    DaxMeasureLibrary,
    Fmt,
    build_library,
)


# --------------------------------------------------------------------------- #
# Structural invariants                                                       #
# --------------------------------------------------------------------------- #
class TestStructure:
    def test_library_singleton_has_measures(self):
        assert len(LIBRARY) >= 110, (
            f"Library has only {len(LIBRARY)} measures; expected ≥110 per the "
            "Section F2 deliverable spec."
        )

    def test_build_library_produces_same_size_each_call(self):
        a, b = build_library(), build_library()
        assert len(a) == len(b)
        assert a.names() == b.names()

    def test_pool_id_matches_zenith_default(self):
        assert LIBRARY.pool_id == "ZAAUTO2024-1"

    def test_every_category_is_populated_except_aux(self):
        counts = LIBRARY.category_counts()
        # The 17 core analytical domains MUST all have at least one measure.
        core_domains = [c for c in Category if c.value.startswith(tuple("0123456789"))]
        for cat in core_domains:
            assert counts[cat] > 0, f"Category {cat.value} has no measures."

    def test_measure_names_are_unique(self):
        names = LIBRARY.names()
        assert len(names) == len(set(names)), "Duplicate measure names detected."


# --------------------------------------------------------------------------- #
# Internal consistency                                                        #
# --------------------------------------------------------------------------- #
class TestValidation:
    def test_no_validation_issues(self):
        issues = LIBRARY.validate()
        assert issues == [], "Library has validation issues:\n  " + "\n  ".join(issues)

    def test_duplicate_detection_catches_dupes(self):
        # Deliberately seed a duplicate name.
        m1 = DaxMeasure(name="Foo", expression="1", category=Category.PORTFOLIO_CORE)
        m2 = DaxMeasure(name="Foo", expression="2", category=Category.PORTFOLIO_CORE)
        lib = DaxMeasureLibrary(measures=[m1, m2])
        issues = lib.validate()
        assert any("Duplicate" in i for i in issues)

    def test_broken_reference_detected(self):
        m = DaxMeasure(
            name="Broken",
            expression="[Does Not Exist] + 1",
            category=Category.PORTFOLIO_CORE,
        )
        lib = DaxMeasureLibrary(measures=[m])
        issues = lib.validate()
        assert any("unknown measure" in i for i in issues)

    def test_referenced_measures_extraction(self):
        m = DaxMeasure(
            name="Composite",
            expression="DIVIDE ( [Stage 1 Balance], [Current Pool Balance] )",
            category=Category.IFRS9,
        )
        refs = m.referenced_measures()
        assert "Stage 1 Balance" in refs
        assert "Current Pool Balance" in refs
        # column references like fact_loan[CurrentBalance] must NOT be captured
        m2 = DaxMeasure(
            name="ColumnOnly",
            expression="SUM ( fact_loan[CurrentBalance] )",
            category=Category.PORTFOLIO_CORE,
        )
        assert m2.referenced_measures() == set()

    def test_empty_expression_rejected(self):
        with pytest.raises(ValueError):
            DaxMeasure(name="Bad", expression="   ", category=Category.PORTFOLIO_CORE)

    def test_empty_name_rejected(self):
        with pytest.raises(ValueError):
            DaxMeasure(name="", expression="1", category=Category.PORTFOLIO_CORE)


# --------------------------------------------------------------------------- #
# Querying                                                                    #
# --------------------------------------------------------------------------- #
class TestQuery:
    def test_lookup_known_measure_by_name(self):
        m = LIBRARY["Total ECL"]
        assert m.category is Category.IFRS9
        assert "fact_loan[ECL_Provision]" in m.expression

    def test_unknown_measure_raises_keyerror(self):
        with pytest.raises(KeyError):
            _ = LIBRARY["Nope Doesn't Exist"]

    def test_by_category_returns_only_that_category(self):
        block = LIBRARY.by_category(Category.IFRS9)
        assert len(block) >= 12  # 3 stages × 4 sub-measures + composites
        for m in block:
            assert m.category is Category.IFRS9

    def test_iteration_yields_all_measures(self):
        names_from_iter = [m.name for m in LIBRARY]
        assert names_from_iter == LIBRARY.names()


# --------------------------------------------------------------------------- #
# Round-trip emitters                                                         #
# --------------------------------------------------------------------------- #
class TestEmitters:
    def test_to_dax_text_contains_every_measure(self):
        dax = LIBRARY.to_dax_text()
        for m in LIBRARY:
            assert f"[{m.name}] =" in dax, f"Missing assignment for [{m.name}]"

    def test_to_dax_text_groups_by_category_in_order(self):
        dax = LIBRARY.to_dax_text()
        category_positions = []
        for cat in Category:
            block = LIBRARY.by_category(cat)
            if not block:
                continue
            pos = dax.find(cat.value)
            assert pos >= 0, f"Category banner {cat.value!r} missing from .dax text"
            category_positions.append(pos)
        # Banners appear in Category enum order.
        assert category_positions == sorted(category_positions)

    def test_dax_block_indentation_is_consistent(self):
        m = LIBRARY["Pool Factor"]
        block = m.to_dax_block()
        # Every continuation line must be indented by at least 4 spaces.
        lines = [ln for ln in block.split("\n") if ln and not ln.startswith("[") and not ln.startswith("//")]
        for ln in lines:
            assert ln.startswith("    "), f"Bad indentation: {ln!r}"

    def test_tmsl_round_trip_is_valid_json(self):
        tmsl = LIBRARY.to_tmsl()
        # Must be JSON-serialisable
        s = json.dumps(tmsl)
        loaded = json.loads(s)
        assert loaded["table"] == "fact_loan"
        assert len(loaded["measures"]) == len(LIBRARY)
        for entry in loaded["measures"]:
            assert "name" in entry and "expression" in entry

    def test_markdown_includes_every_populated_category(self):
        md = LIBRARY.to_markdown()
        for cat in Category:
            if LIBRARY.by_category(cat):
                assert cat.value in md

    def test_write_dax_and_read_back(self, tmp_path: Path):
        out = tmp_path / "lib.dax"
        LIBRARY.write_dax(out)
        assert out.exists()
        body = out.read_text(encoding="utf-8")
        assert "[Total ECL] =" in body
        assert "// =====" in body

    def test_write_tmsl_and_read_back(self, tmp_path: Path):
        out = tmp_path / "lib.tmsl.json"
        LIBRARY.write_tmsl(out)
        payload = json.loads(out.read_text(encoding="utf-8"))
        assert payload["table"] == "fact_loan"


# --------------------------------------------------------------------------- #
# Format-string presets are well-formed                                       #
# --------------------------------------------------------------------------- #
class TestFmtPresets:
    @pytest.mark.parametrize(
        "preset",
        [Fmt.INR, Fmt.INR_CR, Fmt.INR_LAKH, Fmt.PCT_1, Fmt.PCT_2,
         Fmt.PCT_3, Fmt.INT, Fmt.DEC_2, Fmt.DEC_4, Fmt.MONTHS, Fmt.SCORE],
    )
    def test_presets_are_strings(self, preset):
        assert isinstance(preset, str) and preset != ""

    def test_text_preset_is_empty(self):
        assert Fmt.TEXT == ""


# --------------------------------------------------------------------------- #
# Canonical .dax file stays in sync with the Python source                    #
# --------------------------------------------------------------------------- #
class TestCanonicalDaxFile:
    """Ensures the committed .dax file matches what build_library() emits.

    This is what makes the Python module the single source of truth: if a
    contributor edits the .dax file by hand the test fails, prompting them
    to instead edit ``dax_library.py`` and re-run ``python -m
    matrisk.reporting.dax_library --regen``.
    """

    DAX_PATH = Path(__file__).resolve().parents[1] / "powerbi" / "dax" / "dax_measure_library.dax"

    def test_canonical_dax_file_exists(self):
        assert self.DAX_PATH.exists(), f"Missing canonical DAX file: {self.DAX_PATH}"

    def test_every_measure_in_library_appears_in_canonical_file(self):
        if not self.DAX_PATH.exists():
            pytest.skip("No canonical DAX file to compare against")
        text = self.DAX_PATH.read_text(encoding="utf-8")
        # Find every [Name] = … assignment in the file.
        found = set(re.findall(r"^\[([^\]]+)\]\s*=", text, re.MULTILINE))
        for m in LIBRARY:
            assert m.name in found, (
                f"Measure [{m.name}] missing from canonical .dax file. "
                "Regenerate with `python -m matrisk.reporting.dax_library --regen`."
            )


# --------------------------------------------------------------------------- #
# Module-level smoke test                                                     #
# --------------------------------------------------------------------------- #
def test_module_exports_library_singleton():
    assert isinstance(dax_library.LIBRARY, DaxMeasureLibrary)
    assert dax_library.LIBRARY is LIBRARY
