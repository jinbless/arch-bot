"""V1-1: guide_code.py 단위 테스트 (14 케이스)."""
import pytest
from lib.guide_code import (
    parse_guide_filename,
    guide_code_to_short_code,
    validate_guide_code,
    validate_short_code,
)


class TestParseGuideFilename:
    def test_standard_space(self):
        r = parse_guide_filename("A-G-4-2025 이동식 사다리.pdf", "A")
        assert r["shortCode"] == "AG4"
        assert r["year"] == 2025
        assert r["domain"] == "A"

    def test_old_format(self):
        r = parse_guide_filename("C-103-2014 굴착공사.pdf", "C")
        assert r["shortCode"] == "C103"
        assert r["year"] == 2014

    def test_numeric_start(self):
        r = parse_guide_filename("3-65-2023 화학물질.pdf", "B")
        assert r["shortCode"] == "365"
        assert r["year"] == 2023

    def test_underscore_delimiter(self):
        r = parse_guide_filename("E-182-2021_정전기에.pdf", "E")
        assert r["shortCode"] == "E182"
        assert r["year"] == 2021

    def test_space_in_code(self):
        r = parse_guide_filename("D-27- 2021 수소.pdf", "D")
        assert r["shortCode"] == "D27"
        assert r["year"] == 2021

    def test_numeric_prefix(self):
        r = parse_guide_filename("347896_P-79-2011.pdf", "B")
        assert r["shortCode"] == "P79"
        assert r["year"] == 2011

    def test_invalid_file(self):
        r = parse_guide_filename("not_a_guide.txt", "A")
        assert r is None


class TestGuideCodeToShortCode:
    def test_ag4(self):
        assert guide_code_to_short_code("A-G-4-2025") == "AG4"

    def test_dc13(self):
        assert guide_code_to_short_code("D-C-13-2026") == "DC13"

    def test_c103(self):
        assert guide_code_to_short_code("C-103-2014") == "C103"


class TestValidateGuideCode:
    def test_valid(self):
        assert validate_guide_code("A-G-4-2025") is True

    def test_invalid_short(self):
        assert validate_guide_code("ABC") is False


class TestValidateShortCode:
    def test_valid(self):
        assert validate_short_code("AG4") is True

    def test_invalid_lowercase(self):
        assert validate_short_code("a") is False
