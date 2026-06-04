#!/usr/bin/env python3
"""GuideRef가 §섹션 dict를 GuideSectionRef로 coerce하고 model_dump(API 응답)에 싣는지 (LLM 무호출)."""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8")
from app.models.analysis import GuideRef  # noqa: E402

gr = GuideRef(
    guide_code="B-M-36-2026", title="프레스 위험방지에 관한 기술지원규정",
    relevance_score=0.9, mapping_type="hybrid_semantic_rerank",
    relevant_sections=[
        {"section_title": "5.4.1", "excerpt": "광전자식 방호장치 ...", "section_type": "standard"},
        {"section_title": "5.3.6", "excerpt": "양수조작식 ...", "section_type": "standard"},
    ],
)
dumped = gr.model_dump()
secs = dumped["relevant_sections"]
assert isinstance(secs, list) and len(secs) == 2, secs
assert secs[0]["section_title"] == "5.4.1", secs
assert secs[0]["excerpt"].startswith("광전자식"), secs
# 빈 입력도 안전
assert GuideRef(guide_code="X", title="y", relevance_score=0, mapping_type="z").model_dump()["relevant_sections"] == []
print("OK — GuideRef §섹션 coercion + model_dump 정상:")
for s in secs:
    print(f"   § {s['section_title']}  ({s['excerpt'][:18]})")
