"""V6: 에이전트 프롬프트 구조 검증."""
import re
from pathlib import Path

import pytest
import sys
sys.path.insert(0, str(Path(__file__).resolve().parent))
from conftest import AGENTS_DIR, SCHEMA_DIR


class TestStep1VlmParsePrompt:
    @pytest.fixture(autouse=True)
    def load(self):
        self.content = (AGENTS_DIR / "step1-vlm-parse-prompt.md").read_text(encoding="utf-8")

    def test_references_v2_schema(self):
        assert "guide-text-v2" in self.content

    def test_v2_schema_exists(self):
        assert (SCHEMA_DIR / "guide-text-v2.schema.json").exists()

    def test_no_shared_reference(self):
        assert "shared/kosha-guides" not in self.content

    def test_absolute_rules(self):
        assert "원문 보존" in self.content
        assert "additionalProperties" in self.content
        assert "parsedBy" in self.content


class TestStep4EntityExtraction:
    @pytest.fixture(autouse=True)
    def load(self):
        self.content = (AGENTS_DIR / "step4-entity-extraction.md").read_text(encoding="utf-8")

    def test_references_ci_schema(self):
        assert "ci-file.schema.json" in self.content

    def test_ci_schema_exists(self):
        assert (SCHEMA_DIR / "ci-file.schema.json").exists()

    def test_binding_force_enums(self):
        assert "MANDATORY" in self.content
        assert "RECOMMENDED" in self.content

    def test_entity_id_patterns(self):
        assert "CI-" in self.content
        assert "DT-" in self.content
        assert "WP-" in self.content
        assert "ES-" in self.content
        assert "DR-" in self.content
