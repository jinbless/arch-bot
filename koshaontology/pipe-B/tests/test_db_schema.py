"""V5: DB 스키마 검증."""
import json
import re

import pytest
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parent))
from conftest import DB_DIR, SCHEMA_DIR, SCRIPTS_DIR


class TestSchemaCodeConsistency:
    """V5-2: schema_pb.sql과 ci_identifier.py, ci-file.schema.json의 ENUM 정합성."""

    @pytest.fixture(autouse=True)
    def load(self):
        self.sql = (DB_DIR / "schema_pb.sql").read_text(encoding="utf-8")
        self.ci_schema = json.loads(
            (SCHEMA_DIR / "ci-file.schema.json").read_text(encoding="utf-8")
        )

    def test_binding_force_enums_match(self):
        sql_enums = set(re.findall(r"'(MANDATORY|RECOMMENDED)'", self.sql))
        schema_bf = set(
            self.ci_schema["properties"]["checklistItems"]["items"]
            ["properties"]["bindingForce"]["enum"]
        )
        assert sql_enums == schema_bf

    def test_domain_enums_match(self):
        # CHECK(domain IN ('A','B','C','D','E')) 에서 모든 도메인 추출
        m = re.search(r"CHECK\(domain\s+IN\s*\(([^)]+)\)", self.sql)
        assert m, "domain CHECK constraint not found in SQL"
        sql_domains = set(re.findall(r"'([A-E])'", m.group(1)))
        schema_domains = set(
            self.ci_schema["properties"]["metadata"]["properties"]["domain"]["enum"]
        )
        assert sql_domains == schema_domains

    def test_ci_identifier_regex_in_sql(self):
        assert "CI-[A-Z0-9]+-[0-9]+" in self.sql

    def test_dt_identifier_regex_in_sql(self):
        assert "DT-[A-Z0-9]+-[0-9]+" in self.sql

    def test_wp_identifier_regex_in_sql(self):
        assert "WP-[A-Z0-9]+-[0-9]+" in self.sql

    def test_es_identifier_regex_in_sql(self):
        assert "ES-[A-Z0-9]+-[0-9]+" in self.sql

    def test_dr_identifier_regex_in_sql(self):
        assert "DR-[A-Z0-9]+-[0-9]+" in self.sql
