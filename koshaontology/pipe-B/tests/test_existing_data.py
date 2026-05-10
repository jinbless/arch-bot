"""V3: 기존 출력 데이터 검증."""
import json
import re
from pathlib import Path

import pytest
from jsonschema import validate
import sys
sys.path.insert(0, str(Path(__file__).resolve().parent))
from conftest import load_schema, DATA_DIR, SCHEMA_DIR

REPO_ROOT = DATA_DIR.parent.parent.parent


# ── V3-1: guide-inventory.json ──

class TestGuideInventory:
    @pytest.fixture(autouse=True)
    def load_inventory(self):
        self.inv = json.loads(
            (DATA_DIR / "guide-inventory.json").read_text(encoding="utf-8")
        )

    def test_schema_valid(self):
        schema = load_schema("guide-inventory.schema.json")
        validate(self.inv, schema)

    def test_total_equals_1038(self):
        assert self.inv["metadata"]["totalGuides"] == 1038
        assert len(self.inv["guides"]) == 1038

    def test_domain_counts_sum(self):
        dc = self.inv["metadata"]["domainCounts"]
        assert sum(dc.values()) == 1038

    def test_shortcodes_unique(self):
        codes = [g["shortCode"] for g in self.inv["guides"]]
        assert len(codes) == len(set(codes))


# ── V3-2: SR 인덱스 3종 ──

class TestSRArticleIndex:
    @pytest.fixture(autouse=True)
    def load(self):
        self.data = json.loads(
            (DATA_DIR / "sr-article-index.json").read_text(encoding="utf-8")
        )

    def test_total_articles_positive(self):
        assert self.data["totalArticles"] > 0

    def test_entries_have_sr_ids(self):
        for key, entry in self.data["index"].items():
            assert "srIds" in entry
            assert isinstance(entry["srIds"], list)


class TestSRCategoryIndex:
    @pytest.fixture(autouse=True)
    def load(self):
        self.data = json.loads(
            (DATA_DIR / "sr-category-index.json").read_text(encoding="utf-8")
        )

    def test_categories_non_empty_names(self):
        for cat in self.data["index"]:
            assert cat.strip() != ""


class TestSRKeywordIndex:
    @pytest.fixture(autouse=True)
    def load(self):
        self.data = json.loads(
            (DATA_DIR / "sr-keyword-index.json").read_text(encoding="utf-8")
        )

    def test_total_keywords_positive(self):
        assert self.data["totalKeywords"] > 0

    def test_total_srs_626(self):
        assert self.data["totalSRs"] == 626


# ── V3-3: 배치 입력 파일 (D domain) ──

class TestBatchFiles:
    @pytest.fixture(autouse=True)
    def load_batches(self):
        self.batch_dir = DATA_DIR / "ci-batches"
        self.files = sorted(self.batch_dir.glob("pipeb-batch-D-*-input.json"))

    def test_18_batch_files(self):
        assert len(self.files) == 18

    def test_each_batch_domain_D(self):
        for f in self.files:
            data = json.loads(f.read_text(encoding="utf-8"))
            assert data["metadata"]["domain"] == "D"
            assert len(data["guides"]) > 0

    def test_pre_assigned_id_pattern(self):
        pat = re.compile(r"^CI-[A-Z0-9]+-001$")
        for f in self.files:
            data = json.loads(f.read_text(encoding="utf-8"))
            for g in data["guides"]:
                assert pat.match(g["preAssignedIdRange"]["start"])


# ── V3-4: v2-compatible 레거시 파싱 ──

LEGACY_PARSED = REPO_ROOT / "kosha-guides" / "parsed"


@pytest.mark.parametrize("short_code", ["AG10", "BE7", "D28"])
def test_legacy_v2_schema(short_code):
    fp = LEGACY_PARSED / f"guide-{short_code}.json"
    if not fp.exists():
        pytest.skip(f"guide-{short_code}.json not found")
    doc = json.loads(fp.read_text(encoding="utf-8"))
    schema = load_schema("guide-text-v2.schema.json")
    validate(doc, schema)
