"""V1-2: ci_identifier.py 단위 테스트 (12 케이스)."""
import pytest
from lib.ci_identifier import (
    generate_ci_id,
    generate_dt_id,
    generate_wp_id,
    generate_es_id,
    generate_dr_id,
    validate_entity_id,
)


class TestGenerateIds:
    def test_ci_dc13_001(self):
        assert generate_ci_id("DC13", 1) == "CI-DC13-001"

    def test_ci_ag4_015(self):
        assert generate_ci_id("AG4", 15) == "CI-AG4-015"

    def test_dt(self):
        assert generate_dt_id("AG4", 1) == "DT-AG4-001"

    def test_wp_01(self):
        assert generate_wp_id("AG4", 1) == "WP-AG4-01"

    def test_wp_99(self):
        assert generate_wp_id("AG4", 99) == "WP-AG4-99"

    def test_es(self):
        assert generate_es_id("AG4", 1) == "ES-AG4-001"

    def test_dr(self):
        assert generate_dr_id("DC13", 1) == "DR-DC13-001"


class TestValidateEntityId:
    def test_valid_ci(self):
        assert validate_entity_id("CI-DC13-001", "CI") is True

    def test_lowercase_ci(self):
        assert validate_entity_id("CI-dc13-001", "CI") is False

    def test_valid_wp(self):
        assert validate_entity_id("WP-AG4-01", "WP") is True

    def test_wrong_prefix(self):
        assert validate_entity_id("XX-AG4-001", "CI") is False

    def test_invalid_type_raises(self):
        with pytest.raises(ValueError):
            validate_entity_id("CI-AG4-001", "INVALID")
