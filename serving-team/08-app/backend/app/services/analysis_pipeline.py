from __future__ import annotations

import json
import logging
import os
import uuid
from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Any, Optional

from sqlalchemy.orm import Session

from app.db import crud
from app.models.analysis import (
    AnalysisResponse,
    ExcludedCandidate,
    GuideRef,
    HazardGuideRelation,
    HazardItem,
    UnmappedSafetyTerm,
)
from app.models.hazard import (
    CorrectiveAction,
    Finding,
    PenaltyPath,
    ProcedureStep,
    ReasoningTrace,
    RiskFeature,
    RiskLevel,
    SituationMatch,
    StandardProcedure,
    VisualCue,
    VisualObservation,
)
from app.services import (
    guide_recommendation_service,
    match_fusion_service,
    penalty_path_service,
    risk_rule_service,
    situation_frame_service,
    situation_assessment_service,
    sr_lookup_service,
)
from app.services.hazard_normalizer import (
    normalize_hazards_array,
    normalize_risk_feature_candidates,
)
from app.services.she_matcher import (  # WS-SAFETY-5: 불안전 상태 카탈로그(표시용)
    UNSAFE_ENVIRONMENTAL_STATES,
    UNSAFE_PPE_STATES,
)
from app.services.hazard_to_guide_service import match_hazards_to_guides, _semantic_attach_enabled
from app.services.hazard_to_ci_service import match_hazards_to_ci
from app.services.industry_context import infer_industry_context
from app.utils.taxonomy import get_feature_label


# ⭐ Hazard-Direct Pivot Phase 3 Day 3 — A/B mode.
# off=기존 SHE-based path만 (control)
# parallel=두 path 모두 (결과 union, default for 검증)
# primary=hazard-direct 우선 (SHE fallback)
HAZARD_DIRECT_MODE = os.environ.get("HAZARD_DIRECT_MODE", "parallel").lower()


@dataclass
class AnalysisRunInput:
    result: dict
    analysis_type: str
    input_preview: str
    full_description: Optional[str] = None
    declared_industry_text: Optional[str] = None


@dataclass
class AnalysisKnowledgeContext:
    canonical: dict
    risk_features: list[RiskFeature]
    industry_contexts: list[str]
    observable_violation_signal: bool
    she_matches: list[Any]
    actionable_matches: list[Any]
    sr_ids: list[str]
    direct_sr_ids: list[str]
    situation_frame: dict[str, Any]
    checklist_rows: list[dict]
    guide_rows: list[dict]
    penalty_paths: list[PenaltyPath]
    finding_status: str
    penalty_exposure_status: str
    # Runtime 4번 채널 — F.3.5 자율 학습 환류 input pool (analysis_log 확장 hook).
    normalizer_unknown_codes: list[str] = field(default_factory=list)
    raw_vision_features: list = field(default_factory=list)
    # ⭐ Hazard-Direct Pivot Phase 3 Day 3 — hazard-direct path 산출
    hazards_payload: list[dict] = field(default_factory=list)  # raw hazards[] from GPT
    hazard_guide_relations: list[dict] = field(default_factory=list)
    hazard_canonical: dict = field(default_factory=dict)  # normalize_hazards_array 결과
    hazard_direct_mode: str = "off"


class AnalysisPipeline:
    """Build the product response from normalized LLM observations.

    AnalysisService owns transport concerns. This pipeline owns business flow:
    observation -> risk features -> SHE/SR -> guide/actions -> penalties.
    """

    async def run(self, db: Session, run_input: AnalysisRunInput) -> AnalysisResponse:
        analysis_id = str(uuid.uuid4())
        analyzed_at = datetime.now()

        observations = self._build_observations(run_input.result)
        context_text = self._context_text(
            run_input.result,
            run_input.full_description,
            run_input.input_preview,
        )
        visual_cues = [cue.text for obs in observations for cue in obs.visual_cues]

        knowledge = self._build_knowledge_context(
            db=db,
            result=run_input.result,
            observations=observations,
            context_text=context_text,
            visual_cues=visual_cues or [context_text],
            declared_industry_text=run_input.declared_industry_text,
        )

        excluded_candidates = await self._apply_llm_rerank(
            knowledge=knowledge,
            observations=observations,
            visual_cues=visual_cues or [context_text],
            declared_industry_text=run_input.declared_industry_text,
        )

        situation_matches = self._build_situation_matches(knowledge.she_matches)
        article_ids = sr_lookup_service.article_ids_for_srs(db, knowledge.sr_ids)
        findings = self._build_findings(
            status=knowledge.finding_status,
            observations=observations,
            situation_matches=situation_matches,
            sr_ids=knowledge.sr_ids,
        )
        reasoning_trace = self._build_reasoning_trace(
            observations=observations,
            risk_features=knowledge.risk_features,
            situation_matches=situation_matches,
            sr_ids=knowledge.sr_ids,
            article_ids=article_ids,
            guide_rows=knowledge.guide_rows,
            checklist_rows=knowledge.checklist_rows,
            penalty_paths=knowledge.penalty_paths,
        )

        summary = run_input.result.get("overall_assessment") or self._summary(
            observations=observations,
            findings=findings,
            penalty_paths=knowledge.penalty_paths,
        )
        overall_risk_level = self._overall_risk_level(
            observations,
            knowledge.finding_status,
            knowledge.hazards_payload,
        )

        response = AnalysisResponse(
            analysis_id=analysis_id,
            analysis_type=run_input.analysis_type,
            overall_risk_level=RiskLevel(overall_risk_level),
            summary=summary,
            observations=observations,
            risk_features=knowledge.risk_features,
            situation_matches=situation_matches,
            findings=findings,
            immediate_actions=self._build_immediate_actions(
                knowledge.checklist_rows,
                run_input.result.get("immediate_actions", []),
            ),
            standard_procedures=self._build_standard_procedures(knowledge.guide_rows),
            penalty_paths=knowledge.penalty_paths,
            reasoning_trace=reasoning_trace,
            finding_status=knowledge.finding_status,
            penalty_exposure_status=knowledge.penalty_exposure_status,
            excluded_candidates=excluded_candidates,
            # ⭐ Hazard-Direct Pivot 신규 응답 필드
            hazards=self._build_hazard_items(
                knowledge.hazards_payload,
                knowledge.hazard_canonical,
            ),
            hazard_guide_relations=self._build_hazard_guide_relations(
                knowledge.hazard_guide_relations,
            ),
            unmapped_safety_terms=self._build_unmapped_safety_terms(  # WS-SAFETY-5 (표시전용)
                run_input.result,
                knowledge.normalizer_unknown_codes,
            ),
            analyzed_at=analyzed_at,
        )

        self._persist_response(
            db=db,
            response=response,
            input_preview=run_input.input_preview,
            summary=summary,
            overall_risk_level=overall_risk_level,
        )
        return response

    def _build_knowledge_context(
        self,
        db: Session,
        result: dict,
        observations: list[VisualObservation],
        context_text: str,
        visual_cues: list[str],
        declared_industry_text: Optional[str],
    ) -> AnalysisKnowledgeContext:
        normalized = normalize_risk_feature_candidates(
            result.get("risk_feature_candidates", []),
            context_text=context_text,
        )
        canonical = risk_rule_service.apply_risk_rules(
            normalized,
            db,
            allow_context_only_inference=False,
        )
        risk_features = self._build_risk_features(canonical, normalized)
        industry_context = infer_industry_context(
            work_contexts=canonical["work_contexts"],
            text=context_text,
            declared=declared_industry_text,
        )
        situation_frame = situation_frame_service.build_situation_frame(
            canonical=canonical,
            normalized=normalized,
            visual_cues=visual_cues,
            context_text=" ".join(filter(None, [declared_industry_text, context_text])),
            industry_contexts=industry_context.active_industries,
        ).to_dict()
        high_severity_observation = any(
            obs.severity == "HIGH" and obs.confidence >= 0.7 for obs in observations
        )
        observable_violation_signal = (
            situation_assessment_service.has_observable_violation_signal(
                normalized=normalized,
                high_severity_observation=high_severity_observation,
                context_text=context_text,
            )
        )

        she_matches = situation_assessment_service.match_situational_patterns(
            db=db,
            canonical=canonical,
            visual_cues=visual_cues,
            industry_contexts=industry_context.active_industries,
        )
        actionable_matches = [
            match for match in she_matches
            if observable_violation_signal
            and match.match_status in situation_assessment_service.ACTIONABLE_MATCH_STATUSES
        ]

        she_sr_ids = [
            sr_id
            for match in actionable_matches
            for sr_id in match.applies_sr_ids
        ]
        direct_sr_ids = [
            sr_id
            for match in she_matches
            if situation_assessment_service.is_direct_penalty_match(match)
            for sr_id in match.applies_sr_ids
        ]

        sr_results = []
        if actionable_matches or observable_violation_signal:
            sr_results = sr_lookup_service.query_safety_requirements(
                db,
                canonical["accident_types"],
                canonical["hazardous_agents"],
                canonical["work_contexts"],
                industry_contexts=industry_context.active_industries,
            )
        sr_ids = self._unique([*she_sr_ids, *[sr["identifier"] for sr in sr_results]])
        direct_sr_ids = self._unique(direct_sr_ids)

        recommendation_matches = actionable_matches
        recommendation_risk_features = risk_features if observable_violation_signal else []

        # ⭐ Three-Worlds: O facets로 CI/Guide 독립 facet 매칭 + corroboration fusion.
        # 전이 라우팅(SR→CI junction, CI-count Guide) 폐기. checklist_rows/guide_rows 계약은
        # 유지 → 다운스트림 응답 조립(_build_immediate_actions/_build_standard_procedures) 무변경.
        # SR 쿼리와 동일 게이트(actionable/observable) — negative case false positive 방지.
        checklist_rows: list[dict] = []
        guide_rows: list[dict] = []
        if actionable_matches or observable_violation_signal:
            _fusion = match_fusion_service.build_recommendation_rows(
                db,
                canonical["accident_types"],
                canonical["hazardous_agents"],
                canonical["work_contexts"],
                ci_limit=12,
                guide_limit=6,
                industry_contexts=industry_context.active_industries,
            )
            checklist_rows = _fusion["checklist_rows"]
            guide_rows = _fusion["guide_rows"]
        penalty_candidates = penalty_path_service.get_penalty_candidates(
            sr_ids,
            direct_sr_ids=direct_sr_ids,
        )
        finding_status = self._finding_status(
            actionable_matches=actionable_matches,
            she_matches=she_matches,
            sr_ids=sr_ids,
            risk_features=risk_features,
            observable_violation_signal=observable_violation_signal,
        )
        penalty_paths = penalty_path_service.build_penalty_paths(
            penalty_candidates,
            finding_status=finding_status,
        )

        # ⭐ Hazard-Direct Pivot Phase 3 Day 3 — hazards[] path 병행 실행.
        # mode=off 일 때만 skip. parallel(default)/primary 모두 hazards[] 산출 채움.
        hazards_payload: list[dict] = list(result.get("hazards") or [])
        hazard_canonical: dict = {}
        hazard_guide_relations: list[dict] = []
        hazard_sr_ids: list[str] = []
        if HAZARD_DIRECT_MODE != "off" and hazards_payload:
            try:
                hazard_canonical = normalize_hazards_array(
                    hazards_payload,
                    context_text=context_text,
                )
                hazard_guide_relations, hazard_sr_ids = match_hazards_to_guides(
                    db=db,
                    hazards=hazards_payload,
                    canonical=hazard_canonical,
                    industry_contexts=industry_context.active_industries,
                    # breadth 게이팅: IMAGE risk_features의 work_context(예: 지게차→VEHICLE)를
                    # hazard-direct에 전달 → 광범위 accident(COLLISION) 단독 매칭의 오매칭 억제.
                    context_work_contexts=canonical.get("work_contexts") or [],
                )
                # primary mode: hazard-direct가 SR ids를 우선 (penalty path는 본 sprint 비변경, fallback 보존)
                if HAZARD_DIRECT_MODE == "primary" and hazard_sr_ids:
                    logging.getLogger(__name__).info(
                        f"[HazardDirect-Primary] {len(hazard_sr_ids)} SR ids from hazard-direct path"
                    )
            except Exception as e:  # noqa: BLE001
                logging.getLogger(__name__).warning(
                    f"[HazardDirect] error in pipeline, fallback to legacy path: {e}"
                )

        # 「즉시 조치」 v5화 — GPT 조치/설명 → raw CI 벡터매칭 → guide+섹션 인용으로 checklist_rows 대체.
        # flag off면 match_hazards_to_ci=[] → checklist_rows(legacy) 그대로(무회귀).
        if hazards_payload:
            try:
                sem_ci_rows = match_hazards_to_ci(
                    db, hazards_payload, industry_contexts=industry_context.active_industries
                )
                if sem_ci_rows:
                    checklist_rows = sem_ci_rows
            except Exception as e:  # noqa: BLE001
                logging.getLogger(__name__).warning(f"[HazardToCI] error, keep legacy checklist: {e}")

        # 「표준 개선 절차」 v5화 — 위험요소별(v5) guides를 dedup해 guide_rows로 대체 (flag on).
        # flag off면 hazard_guide_relations는 facet 기반이므로 건드리지 않음(무회귀).
        if _semantic_attach_enabled() and hazard_guide_relations:
            _seen_g: dict = {}
            for _rel in hazard_guide_relations:
                for _g in _rel.get("guides") or []:
                    _gc = _g.get("guide_code")
                    if not _gc:
                        continue
                    _sc = float(_g.get("relevance_score") or 0.0)
                    if _gc not in _seen_g or _sc > _seen_g[_gc]["relevance_score"]:
                        # §섹션 근거(_attach_section_evidence 사후 부착) → evidence_summary로
                        # 표준개선절차 패널에 노출(GuideProcedurePanel이 이미 렌더 — 프론트 변경 불요).
                        _secs = [s.get("section_title") for s in (_g.get("relevant_sections") or [])
                                 if s.get("section_title")]
                        _ev = f"근거 섹션 — {_gc} §{'·'.join(_secs[:3])}" if _secs else None
                        _seen_g[_gc] = {"guide_code": _gc, "title": _g.get("title"),
                                        "relevance_score": _sc, "mapping_type": _g.get("mapping_type"),
                                        "evidence_summary": _ev}
            _sem_guides = sorted(_seen_g.values(), key=lambda x: x["relevance_score"], reverse=True)
            # ── WS-GATE-3: 도메인-부적합 guide hard reject (opt-in, 기본 off=무회귀) ──
            # shadow_validate가 analysis_log write-only로만 쓰이던 도메인 모순 신호를, 기본 served
            # 경로의 semantic attach 직전에서 high-confidence(vetted & conf>=임계)만 hard-drop한다.
            # **semantic(hazard-direct) 후보에만 적용** → facet(CI-corroborated) guide_rows는 무영향
            # (FN 보수; DEEP-1 merge가 facet을 재보존). 전부 드롭 시 _sem_guides=∅ → 아래 overwrite
            # 미발동 → facet guide_rows 생존(FN-safe fallback).
            if _sem_guides:
                from app.services import shadow_reasoner as _shadow
                _industry_ko = declared_industry_text or (
                    industry_context.active_industries[0]
                    if industry_context.active_industries else ""
                )
                _reject = _shadow.domain_reject_codes(
                    _industry_ko, [g["guide_code"] for g in _sem_guides]
                )
                if _reject:
                    _before = len(_sem_guides)
                    _sem_guides = [g for g in _sem_guides if g["guide_code"] not in _reject]
                    logging.getLogger(__name__).info(
                        "[WS-GATE-3] domain-reject dropped %d/%d semantic guides "
                        "(industry=%s): %s",
                        len(_reject), _before, _industry_ko, sorted(_reject),
                    )
            if _sem_guides:
                guide_rows = _sem_guides

        # 「벌칙 3경로」 v5 연결 — semantic SR(정밀, 예: SR-VEHICLE→제179조)을 penalty 후보 풀에 보강(flag on).
        # replay는 hazards[] 미주입 → hazard_sr_ids ∅ → 미발동(무회귀). exposure는 보수적으로 legacy
        # finding_status 유지(과대 promote 방지) — 정밀 조문만 후보에 추가.
        if _semantic_attach_enabled() and hazard_sr_ids:
            sr_ids = self._unique([*hazard_sr_ids, *sr_ids])
            penalty_candidates = penalty_path_service.get_penalty_candidates(
                sr_ids, direct_sr_ids=direct_sr_ids
            )
            penalty_paths = penalty_path_service.build_penalty_paths(
                penalty_candidates, finding_status=finding_status
            )

        return AnalysisKnowledgeContext(
            canonical=canonical,
            risk_features=risk_features,
            industry_contexts=industry_context.active_industries,
            observable_violation_signal=observable_violation_signal,
            she_matches=she_matches,
            actionable_matches=actionable_matches,
            sr_ids=sr_ids,
            direct_sr_ids=direct_sr_ids,
            situation_frame=situation_frame,
            checklist_rows=checklist_rows,
            guide_rows=guide_rows,
            penalty_paths=penalty_paths,
            finding_status=finding_status,
            penalty_exposure_status=self._penalty_exposure_status(penalty_paths),
            normalizer_unknown_codes=list(normalized.get("unknown_codes") or []),
            raw_vision_features=list(result.get("risk_feature_candidates") or []),
            hazards_payload=hazards_payload,
            hazard_guide_relations=hazard_guide_relations,
            hazard_canonical=hazard_canonical,
            hazard_direct_mode=HAZARD_DIRECT_MODE,
        )

    def _build_observations(self, result: dict) -> list[VisualObservation]:
        cues = [
            VisualCue(
                text=item.get("text", ""),
                cue_type=item.get("cue_type", "visual"),
                confidence=float(item.get("confidence", 0) or 0),
            )
            for item in result.get("visual_cues", [])
            if item.get("text")
        ]
        observations = []
        for index, item in enumerate(result.get("visual_observations", []), start=1):
            observations.append(
                VisualObservation(
                    observation_id=f"OBS-{index:03d}",
                    text=item.get("text", ""),
                    confidence=float(item.get("confidence", 0) or 0),
                    severity=item.get("severity", "MEDIUM"),
                    visual_cues=cues,
                )
            )
        if not observations and cues:
            observations.append(
                VisualObservation(
                    observation_id="OBS-001",
                    text="; ".join(cue.text for cue in cues[:3]),
                    confidence=max(cue.confidence for cue in cues),
                    severity="MEDIUM",
                    visual_cues=cues,
                )
            )
        return observations

    def _context_text(
        self,
        result: dict,
        full_description: Optional[str],
        input_preview: str,
    ) -> str:
        parts = [full_description or input_preview]
        parts.extend(item.get("text", "") for item in result.get("visual_observations", []))
        parts.extend(item.get("text", "") for item in result.get("visual_cues", []))
        parts.extend(item.get("text", "") for item in result.get("risk_feature_candidates", []))
        return " ".join(part for part in parts if part)

    def _build_risk_features(self, canonical: dict, normalized: dict) -> list[RiskFeature]:
        axis_fields = [
            ("accident_type", "accident_types"),
            ("hazardous_agent", "hazardous_agents"),
            ("work_context", "work_contexts"),
        ]
        features = []
        for axis, field in axis_fields:
            for code in canonical.get(field, []):
                features.append(
                    RiskFeature(
                        axis=axis,
                        code=code,
                        label=get_feature_label(code),
                        source_text="; ".join(normalized.get("alias_resolved", [])[:3]) or None,
                        confidence=float(canonical.get("confidence", 0) or 0),
                    )
                )
        return features

    def _build_situation_matches(self, she_matches) -> list[SituationMatch]:
        return [
            SituationMatch(
                pattern_id=match.she_id,
                title=getattr(match, "name", None),
                status=getattr(match, "match_status", "candidate"),
                score=float(getattr(match, "match_score", 0) or 0),
                matched_features=list(getattr(match, "matched_dims", []) or []),
                visual_trigger_hits=list(getattr(match, "status_reasons", []) or []),
                applies_sr_ids=list(getattr(match, "applies_sr_ids", []) or []),
                applies_ci_ids=list(getattr(match, "applies_ci_ids", []) or []),
            )
            for match in she_matches
        ]

    def _build_immediate_actions(
        self,
        checklist_rows: list[dict],
        llm_actions: list[str],
    ) -> list[CorrectiveAction]:
        actions = []
        seen = set()
        for row in checklist_rows:
            text = row.get("text")
            if not text or text in seen:
                continue
            seen.add(text)
            actions.append(
                CorrectiveAction(
                    action_id=row.get("identifier") or f"CI-{len(actions) + 1:03d}",
                    title=text,
                    description=row.get("evidence_summary") or row.get("source_section"),
                    source_type="guide:ChecklistItem",
                    source_id=row.get("identifier"),
                    urgency="immediate" if row.get("binding_force") == "MANDATORY" else "planned",
                    confidence=float(row.get("relevance_score", 0.9) or 0.9),
                )
            )
        for text in llm_actions:
            if not text or text in seen:
                continue
            seen.add(text)
            actions.append(
                CorrectiveAction(
                    action_id=f"LLM-ACTION-{len(actions) + 1:03d}",
                    title=text,
                    source_type="app:VisualObservation",
                    urgency="immediate",
                    confidence=0.5,
                )
            )
        return actions[:10]

    def _build_hazard_items(
        self,
        hazards_payload: list[dict],
        hazard_canonical: dict,
    ) -> list[HazardItem]:
        """⭐ Hazard-Direct Pivot — GPT hazards[] → Pydantic HazardItem 변환.

        mapped_codes는 normalize_hazards_array의 hazard_name_to_codes 활용 (audit).
        """
        name_to_codes: dict[str, list[str]] = (hazard_canonical or {}).get("hazard_name_to_codes", {}) or {}
        items: list[HazardItem] = []
        for h in hazards_payload or []:
            name = (h.get("name") or "").strip()
            if not name:
                continue
            items.append(
                HazardItem(
                    name=name,
                    risk_level=str(h.get("risk_level") or "medium").lower(),
                    location=str(h.get("location") or ""),
                    description=str(h.get("description") or ""),
                    preventive_measures=list(h.get("preventive_measures") or []),
                    mapped_codes=list(name_to_codes.get(name) or []),
                )
            )
        return items

    def _build_hazard_guide_relations(
        self,
        relations_raw: list[dict],
    ) -> list[HazardGuideRelation]:
        """⭐ Hazard-Direct Pivot — match_hazards_to_guides dict → Pydantic 변환."""
        out: list[HazardGuideRelation] = []
        for r in relations_raw or []:
            guides_raw = r.get("guides") or []
            guides = [
                GuideRef(
                    guide_code=str(g.get("guide_code") or ""),
                    title=str(g.get("title") or ""),
                    classification=g.get("classification"),
                    relevance_score=float(g.get("relevance_score") or 0.0),
                    mapping_type=str(g.get("mapping_type") or "sr_ci_link"),
                    ci_hit_count=int(g.get("ci_hit_count") or 0),
                    industry_alignment=g.get("industry_alignment"),
                    top_procedure_title=g.get("top_procedure_title"),
                    # §섹션 근거(_attach_section_evidence 사후 부착) — dict 리스트 → pydantic coerce.
                    relevant_sections=[
                        s for s in (g.get("relevant_sections") or []) if s.get("section_title")
                    ],
                )
                for g in guides_raw
                if g.get("guide_code")
            ]
            out.append(
                HazardGuideRelation(
                    hazard_name=str(r.get("hazard_name") or ""),
                    risk_level=str(r.get("risk_level") or "medium").lower(),
                    location=str(r.get("location") or ""),
                    description=str(r.get("description") or ""),
                    preventive_measures=list(r.get("preventive_measures") or []),
                    mapped_codes=list(r.get("mapped_codes") or []),
                    guides=guides,
                    matched_sr_count=int(r.get("matched_sr_count") or 0),
                )
            )
        return out

    def _build_standard_procedures(self, guide_rows: list[dict]) -> list[StandardProcedure]:
        procedures = []
        for row in guide_rows:
            code = row.get("guide_code")
            title = row.get("title")
            if not code or not title:
                continue
            procedures.append(
                StandardProcedure(
                    procedure_id=code,
                    title=f"{code}: {title}",
                    description=(
                        "관련 KOSHA Guide와 작업 프로세스를 기준으로 표준 개선 절차를 검토합니다."
                        if not row.get("evidence_summary")
                        else row.get("evidence_summary")
                    ),
                    guide_code=code,
                    steps=[
                        ProcedureStep(
                            step_id=step.get("step_id") or f"{code}-STEP-{idx + 1}",
                            order=int(step.get("order") or idx + 1),
                            title=step.get("title") or "작업 절차 검토",
                            safety_measures=step.get("safety_measures"),
                            source_section=step.get("source_section"),
                            source_sr_ids=list(step.get("source_sr_ids") or []),
                        )
                        for idx, step in enumerate(row.get("work_process_steps") or [])
                    ],
                    source_sr_ids=list(row.get("source_sr_ids") or []),
                    source_ci_ids=list(row.get("source_ci_ids") or []),
                    evidence_summary=row.get("evidence_summary"),
                    confidence=float(row.get("relevance_score", 0) or 0),
                    mapping_type=row.get("mapping_type"),  # WS-PROV-3: 부착 출처(표시전용)
                )
            )
        return procedures

    def _build_unmapped_safety_terms(
        self,
        result: dict,
        normalizer_unknown_codes: list[str],
    ) -> list[UnmappedSafetyTerm]:
        """WS-SAFETY-5 (표시전용): GPT가 관찰했으나 폐쇄세계 매칭/스코어링에 쓰이지 못한
        안전 신호를 가시화. finding_status/penalty/매칭에 영향 없음 — '미탐지 ≠ 안전'.
        """
        terms: list[UnmappedSafetyTerm] = []
        seen: set[str] = set()
        for cand in result.get("risk_feature_candidates") or []:
            axis = cand.get("axis")
            text = (cand.get("text") or "").strip()
            if not text or text in seen:
                continue
            if axis == "ppe_state" and text in UNSAFE_PPE_STATES:
                seen.add(text)
                terms.append(UnmappedSafetyTerm(
                    term=text, category="ppe_missing",
                    note="GPT가 불안전 PPE 상태를 관찰 (표준 매칭 미반영 — 추가 확인 필요)",
                ))
            elif axis == "environmental" and text in UNSAFE_ENVIRONMENTAL_STATES:
                seen.add(text)
                terms.append(UnmappedSafetyTerm(
                    term=text, category="environmental_hazard",
                    note="GPT가 불안전 환경 상태를 관찰 (표준 매칭 미반영 — 추가 확인 필요)",
                ))
        for code in normalizer_unknown_codes or []:
            key = f"unknown::{code}"
            if key in seen:
                continue
            seen.add(key)
            terms.append(UnmappedSafetyTerm(
                term=str(code), category="unmapped_code",
                note="해석되지 않은 위험 어휘 (분류 불가 — 안전 보장 아님)",
            ))
        return terms[:20]

    def _build_findings(
        self,
        status: str,
        observations: list[VisualObservation],
        situation_matches: list[SituationMatch],
        sr_ids: list[str],
    ) -> list[Finding]:
        if not observations and not situation_matches and not sr_ids:
            return []
        return [
            Finding(
                finding_id="FINDING-001",
                status=status,
                summary=self._finding_summary(status, observations, sr_ids),
                evidence_strength=self._evidence_strength(status),
                observation_ids=[obs.observation_id for obs in observations],
                situation_pattern_ids=[match.pattern_id for match in situation_matches],
                sr_ids=sr_ids,
            )
        ]

    def _build_reasoning_trace(
        self,
        observations: list[VisualObservation],
        risk_features: list[RiskFeature],
        situation_matches: list[SituationMatch],
        sr_ids: list[str],
        article_ids: list[str],
        guide_rows: list[dict],
        checklist_rows: list[dict],
        penalty_paths: list[PenaltyPath],
    ) -> ReasoningTrace:
        return ReasoningTrace(
            observations=[obs.observation_id for obs in observations],
            risk_features=[feature.code for feature in risk_features],
            situation_patterns=[match.pattern_id for match in situation_matches],
            safety_requirements=sr_ids,
            articles=article_ids,
            guides=[row.get("guide_code") for row in guide_rows if row.get("guide_code")],
            checklist_items=[row.get("identifier") for row in checklist_rows if row.get("identifier")],
            penalty_rules=self._unique(
                rule_id
                for path in penalty_paths
                for rule_id in path.penalty_rule_ids
            ),
        )

    def _persist_response(
        self,
        db: Session,
        response: AnalysisResponse,
        input_preview: str,
        summary: str,
        overall_risk_level: str,
    ) -> None:
        crud.create_product_analysis_record(
            db=db,
            analysis_id=response.analysis_id,
            analysis_type=response.analysis_type,
            overall_risk_level=overall_risk_level,
            summary=summary,
            input_preview=input_preview,
            result_json=json.loads(response.model_dump_json()),
            observations=[
                obs.model_dump(mode="json") for obs in response.observations
            ],
            risk_features=[
                feature.model_dump(mode="json") for feature in response.risk_features
            ],
        )

    def _finding_status(
        self,
        actionable_matches,
        she_matches,
        sr_ids: list[str],
        risk_features: list[RiskFeature],
        observable_violation_signal: bool,
    ) -> str:
        confirmed_matches = [
            match for match in actionable_matches
            if getattr(match, "match_status", "") == "confirmed"
        ]
        candidate_matches = [
            match for match in actionable_matches
            if getattr(match, "match_status", "") == "candidate"
        ]
        if confirmed_matches and sr_ids:
            return "confirmed"
        if candidate_matches and sr_ids:
            if any(self._match_needs_confirmation(match) for match in candidate_matches):
                return "needs_clarification"
            return "suspected"
        if sr_ids:
            return "suspected" if observable_violation_signal else "needs_clarification"
        if she_matches:
            return "needs_clarification" if observable_violation_signal else "not_determined"
        if risk_features:
            return "needs_clarification" if observable_violation_signal else "not_determined"
        return "not_determined"

    def _match_needs_confirmation(self, match) -> bool:
        reasons = set(getattr(match, "status_reasons", []) or [])
        return (
            getattr(match, "match_status", "") == "review_candidate"
            or "confirmation_required" in reasons
            or any(reason.startswith("indirect_") for reason in reasons)
        )

    def _evidence_strength(self, status: str) -> str:
        if status == "confirmed":
            return "high"
        if status == "suspected":
            return "medium"
        return "low"

    async def _apply_llm_rerank(
        self,
        knowledge: AnalysisKnowledgeContext,
        observations: list[VisualObservation],
        visual_cues: list[str],
        declared_industry_text: Optional[str],
    ) -> list[ExcludedCandidate]:
        """Phase B — Embedding pre-filter + LLM rerank.

        env LLM_RERANK_MODE:
          off    : passthrough (0 비용, default)
          shadow : drop/reject 로그만, 실제 제거 안 함
          active : drop/reject candidate 실제 제거

        Quick win Task 2: A hook always-on — early-return 경로에도 analysis_log 기록.
        F.1 mining 입력(normalizer_unknown_codes, raw_vision_features 등)이 mode=off 또는
        guide_rows 빈 시에도 capture됨. 기존: shadow/active 시에만 기록.
        """
        mode = os.environ.get("LLM_RERANK_MODE", "off").lower()
        if mode not in ("shadow", "active"):
            self._log_skipped_analysis(knowledge, observations, declared_industry_text, mode, "mode_off")
            return []
        if not knowledge.guide_rows:
            self._log_skipped_analysis(knowledge, observations, declared_industry_text, mode, "empty_guide_rows")
            return []

        from app.integrations.openai_client import openai_client
        from app.services.guide_domain_profile import get_guide_domain_profile
        from app.services.guide_embedding_filter import (
            GuideEmbeddingFilter,
            build_scene_text,
        )
        from app.services.llm_validator_cache import (
            LlmValidatorCache,
            ValidatorVerdict,
            make_scene_hash,
        )

        embedding_filter = GuideEmbeddingFilter.instance()
        cache = LlmValidatorCache.instance()

        visual_obs_texts = [o.text for o in observations if o.text]
        industry = declared_industry_text or (
            knowledge.industry_contexts[0] if knowledge.industry_contexts else ""
        )
        canonical = knowledge.canonical or {}
        canonical_features = (
            list(canonical.get("accident_types") or [])
            + list(canonical.get("work_contexts") or [])
            + list(canonical.get("hazardous_agents") or [])
        )
        scene_text = build_scene_text(
            visual_observations=visual_obs_texts,
            visual_cues=visual_cues,
            canonical_features=canonical_features,
            industry_contexts=knowledge.industry_contexts,
        )
        candidate_codes = [row.get("guide_code") for row in knowledge.guide_rows if row.get("guide_code")]
        if not candidate_codes:
            self._log_skipped_analysis(knowledge, observations, declared_industry_text, mode, "empty_candidate_codes")
            return []

        filter_result = embedding_filter.filter_candidates(scene_text, candidate_codes)
        excluded: list[ExcludedCandidate] = []

        for guide_code in filter_result.drop:
            guide_row = next(
                (r for r in knowledge.guide_rows if r.get("guide_code") == guide_code),
                None,
            )
            if guide_row is None:
                continue
            sim = filter_result.similarities.get(guide_code, 0.0)
            excluded.append(
                ExcludedCandidate(
                    guide_code=guide_code,
                    title=guide_row.get("title"),
                    verdict="reject",
                    reason=f"embedding similarity {sim:.3f} < 0.25 (도메인 명백히 무관)",
                    confidence=round(1.0 - max(0.0, sim), 4),
                    similarity=sim,
                    source="embedding",
                )
            )

        scene_hash = make_scene_hash(visual_obs_texts, visual_cues, industry)
        logger = logging.getLogger(__name__)
        llm_call_count = 0
        llm_cache_hit_count = 0

        for guide_code in filter_result.gray:
            guide_row = next(
                (r for r in knowledge.guide_rows if r.get("guide_code") == guide_code),
                None,
            )
            if guide_row is None:
                continue
            cached = cache.get(scene_hash, guide_code)
            verdict_obj: Optional[ValidatorVerdict] = cached
            if cached is not None:
                llm_cache_hit_count += 1
            else:
                profile = get_guide_domain_profile(guide_code) or {}
                work_processes = [
                    step.get("title", "")
                    for step in (guide_row.get("work_process_steps") or [])[:5]
                    if step.get("title")
                ]
                try:
                    llm_response = await openai_client.validate_guide_relevance(
                        visual_observations=visual_obs_texts,
                        visual_cues=visual_cues,
                        industry_context=industry,
                        guide_code=guide_code,
                        guide_title=str(guide_row.get("title") or ""),
                        domain_family=str(profile.get("domain_family") or ""),
                        required_context_terms=list(
                            profile.get("required_context_terms") or []
                        ),
                        work_processes=work_processes,
                    )
                    verdict_obj = ValidatorVerdict(
                        verdict=str(llm_response.get("verdict", "accept")),
                        reason=str(llm_response.get("reason", "")),
                        confidence=float(llm_response.get("confidence", 0.0)),
                        ts=datetime.now(timezone.utc).isoformat(),
                    )
                    cache.put(scene_hash, guide_code, verdict_obj)
                    llm_call_count += 1
                except Exception as exc:
                    logger.warning(
                        "LLM validate_guide_relevance failed for %s: %s",
                        guide_code,
                        exc,
                    )
                    continue

            if verdict_obj.is_reject:
                sim = filter_result.similarities.get(guide_code, 0.0)
                excluded.append(
                    ExcludedCandidate(
                        guide_code=guide_code,
                        title=guide_row.get("title"),
                        verdict="reject",
                        reason=verdict_obj.reason,
                        confidence=verdict_obj.confidence,
                        similarity=sim,
                        source="llm",
                    )
                )

        try:
            cache.flush()
        except Exception as exc:
            logger.warning("LlmValidatorCache.flush failed: %s", exc)

        if mode == "active" and excluded:
            excluded_set = {e.guide_code for e in excluded}
            knowledge.guide_rows = [
                r for r in knowledge.guide_rows if r.get("guide_code") not in excluded_set
            ]

        # T2.A: shadow-validate via F.3.2 axioms (best-effort, never blocks)
        from app.services import shadow_reasoner
        try:
            reasoner_rejects = shadow_reasoner.shadow_validate(industry, candidate_codes)
        except Exception as exc:
            logger.warning("shadow_reasoner.shadow_validate failed: %s", exc)
            reasoner_rejects = []

        try:
            self._append_analysis_log(
                scene_hash=scene_hash,
                mode=mode,
                industry=industry,
                visual_obs=visual_obs_texts,
                candidate_codes=candidate_codes,
                filter_result=filter_result,
                excluded=excluded,
                normalizer_unknown_codes=list(knowledge.normalizer_unknown_codes),
                she_match_count=len(knowledge.she_matches),
                raw_vision_features=knowledge.raw_vision_features,
                reasoner_rejects=reasoner_rejects,
            )
        except Exception as exc:
            logger.warning("analysis_log append failed: %s", exc)

        logger.info(
            "LLM rerank mode=%s drop=%d gray=%d (llm_calls=%d cache_hits=%d) excluded=%d",
            mode,
            len(filter_result.drop),
            len(filter_result.gray),
            llm_call_count,
            llm_cache_hit_count,
            len(excluded),
        )
        return excluded

    def _log_skipped_analysis(
        self,
        knowledge: AnalysisKnowledgeContext,
        observations: list[VisualObservation],
        declared_industry_text: Optional[str],
        mode: str,
        skip_reason: str,
    ) -> None:
        """Quick win Task 2 — A hook always-on.

        _apply_llm_rerank early-return 경로에서도 F.1 mining 입력을 capture한다.
        기존: shadow/active 모드에서만 _append_analysis_log 발동 → mode=off 시 데이터 손실.
        해결: 각 early-return 직전에 이 메서드 호출 → analysis_log.jsonl에 항상 기록.

        skip_reason: 'mode_off' / 'empty_guide_rows' / 'empty_candidate_codes'
        """
        from app.services.llm_validator_cache import make_scene_hash

        visual_obs_texts = [o.text for o in observations if o.text]
        visual_cues = [cue.text for obs in observations for cue in obs.visual_cues]
        industry = declared_industry_text or (
            knowledge.industry_contexts[0] if knowledge.industry_contexts else ""
        )
        scene_hash = make_scene_hash(visual_obs_texts, visual_cues, industry)

        # T2.A: shadow-validate via F.3.2 axioms even for skipped paths
        # (mode=off: most analyses go through here in non-shadow envs).
        # Use guide_rows.guide_code as candidate_codes input.
        candidate_codes_skipped: list[str] = []
        try:
            candidate_codes_skipped = [
                r.get("guide_code")
                for r in (knowledge.guide_rows or [])
                if r.get("guide_code")
            ]
        except Exception:
            candidate_codes_skipped = []

        from app.services import shadow_reasoner
        try:
            reasoner_rejects = shadow_reasoner.shadow_validate(
                industry, candidate_codes_skipped
            )
        except Exception as exc:
            logging.getLogger(__name__).warning(
                "shadow_reasoner skipped-path failed: %s", exc
            )
            reasoner_rejects = []

        # rerank-specific fields는 비움 (early-return이므로 not applicable)
        try:
            self._append_analysis_log(
                scene_hash=scene_hash,
                mode=f"{mode}_skipped_{skip_reason}",
                industry=industry,
                visual_obs=visual_obs_texts,
                candidate_codes=[],
                filter_result=None,
                excluded=[],
                normalizer_unknown_codes=list(knowledge.normalizer_unknown_codes),
                she_match_count=len(knowledge.she_matches),
                raw_vision_features=knowledge.raw_vision_features,
                reasoner_rejects=reasoner_rejects,
            )
        except Exception as exc:
            logging.getLogger(__name__).warning(
                "analysis_log skipped-path append failed: %s", exc
            )


    def _append_analysis_log(
        self,
        *,
        scene_hash: str,
        mode: str,
        industry: str,
        visual_obs: list[str],
        candidate_codes: list[str],
        filter_result: Any,
        excluded: list[ExcludedCandidate],
        normalizer_unknown_codes: list[str] | None = None,
        she_match_count: int = 0,
        raw_vision_features: dict | None = None,
        reasoner_rejects: list[dict] | None = None,
    ) -> None:
        """Phase C.1 — append per-analysis log for self-refine mining.

        Quick win Task 2 (A hook always-on): mode='off_skipped_*' / 'shadow_skipped_*'
        / 'active_skipped_*' 도 기록. filter_result=None 시 0 처리.

        T2.A (F.3.1 reasoner shadow channel): reasoner_rejects — F.3.2 axiom이
        도출했을 추가 reject 목록. shadow log만, 실제 reject 안 함. None 또는 빈
        list 시 entry에서 생략.

        Runtime 4번 채널 (F.3.5 environment) — 자율 학습 환류 input pool:
          normalizer_unknown_codes : Layer 1 alias 미등재 새 어휘 후보
          she_match_count          : Layer 2 SHE matcher 매치 수 (0이면 새 SHE 패턴 후보)
          raw_vision_features      : Layer 0 Vision LLM 원본 출력 (정규화 전)
          reasoner_rejects         : Layer 2.5 KB axiom shadow rejections (T2.A)
        """
        valid_mode_prefixes = ("shadow", "active", "off_skipped", "shadow_skipped", "active_skipped")
        if not any(mode.startswith(p) for p in valid_mode_prefixes):
            return
        from pathlib import Path

        backend_app = Path(__file__).resolve().parents[1]
        for ancestor in backend_app.parents:
            artifacts_dir = ancestor / "data-team" / "05-enrichment" / "runtime-artifacts"
            if artifacts_dir.exists():
                log_path = artifacts_dir / "analysis_log.jsonl"
                break
        else:
            return
        # filter_result는 early-return 경로(_log_skipped_analysis)에서 None
        filter_keep = len(filter_result.keep) if filter_result else 0
        filter_gray = len(filter_result.gray) if filter_result else 0
        filter_drop = len(filter_result.drop) if filter_result else 0
        entry = {
            "ts": datetime.now(timezone.utc).isoformat(),
            "mode": mode,
            "scene_hash": scene_hash,
            "industry": industry,
            "visual_obs_count": len(visual_obs),
            "candidate_count": len(candidate_codes),
            "filter_keep": filter_keep,
            "filter_gray": filter_gray,
            "filter_drop": filter_drop,
            "excluded": [
                {
                    "guide_code": e.guide_code,
                    "source": e.source,
                    "reason": e.reason[:100],
                    "similarity": e.similarity,
                }
                for e in excluded
            ],
            "normalizer_unknown_codes": list(normalizer_unknown_codes or []),
            "she_match_count": she_match_count,
            "raw_vision_features": raw_vision_features or {},
        }
        # T2.A: write reasoner_rejects only when non-empty list (avoid noise)
        if reasoner_rejects:
            entry["reasoner_rejects"] = list(reasoner_rejects)
        with log_path.open("a", encoding="utf-8") as f:
            f.write(json.dumps(entry, ensure_ascii=False) + "\n")

    def _penalty_exposure_status(self, penalty_paths: list[PenaltyPath]) -> str:
        if any(path.notice_level == "photo_based" for path in penalty_paths):
            return "direct"
        if penalty_paths:
            return "conditional"
        return "no_penalty"

    def _overall_risk_level(
        self,
        observations: list[VisualObservation],
        finding_status: str,
        hazards_payload: Optional[list[dict]] = None,
    ) -> str:
        # WS-SAFETY-3: hazards[] OR-in — hazard-direct(개방세계)가 high 위험을 직접 봤으면
        #   상단 배지를 절대 녹색 'low/unknown'으로 떨어뜨리지 않는다(상단 vs hazards 카드 모순 제거).
        #   HAZARD_DIRECT_MODE=='off'면 hazards 경로 미사용이므로 존중(무시).
        hazard_high = HAZARD_DIRECT_MODE != "off" and any(
            str(h.get("risk_level", "")).lower() == "high" for h in (hazards_payload or [])
        )
        if finding_status == "confirmed" and any(obs.severity == "HIGH" for obs in observations):
            return "high"
        if hazard_high:
            # 폐쇄세계(SHE/SR)가 confirmed까지 못 갔어도 GPT가 본 high hazard는 묻지 않는다.
            return "high" if finding_status in {"confirmed", "suspected"} else "medium"
        if finding_status in {"confirmed", "suspected"}:
            return "medium"
        # WS-SAFETY-1: '평가 못 함/근거 부족'(not_determined/needs_clarification)을 녹색 'low'로
        #   붕괴시키지 않는다 — '미탐지 ≠ 안전'. assessed_safe(녹색 low) 상태는 D1로 후속(현재 미도입).
        return "unknown"

    def _summary(
        self,
        observations: list[VisualObservation],
        findings: list[Finding],
        penalty_paths: list[PenaltyPath],
    ) -> str:
        if findings:
            penalty_text = " 벌칙 안내 경로가 있습니다." if penalty_paths else ""
            return f"{findings[0].summary}{penalty_text}"
        # WS-SAFETY-1: findings 없음 = 폐쇄세계(SHE/SR)가 위험을 확정 못 함.
        #   '미탐지 ≠ 안전' — 관찰 유무와 무관하게 '판정 불가'를 명시해 녹색 오신호를 차단한다.
        if observations:
            return (
                f"{observations[0].text} (관찰은 되었으나 위험 패턴을 확정하지 못했습니다 — "
                "안전을 보장하지 않으며 추가 현장 확인이 필요합니다.)"
            )
        return "이 입력만으로는 위험 유무를 확정할 수 없습니다 (안전 보장 아님 — 추가 현장 확인 필요)."

    def _finding_summary(
        self,
        status: str,
        observations: list[VisualObservation],
        sr_ids: list[str],
    ) -> str:
        status_label = {
            "confirmed": "확인된 위험",
            "suspected": "의심 위험",
            "needs_clarification": "추가 확인 필요",
            "not_determined": "판단 불가",
        }.get(status, status)
        base = observations[0].text if observations else "관찰 사실 없음"
        if sr_ids:
            return f"{status_label}: {base} 관련 안전요구사항 {len(sr_ids)}건이 연결되었습니다."
        return f"{status_label}: {base}"

    def _unique(self, values) -> list:
        return list(dict.fromkeys(value for value in values if value))


analysis_pipeline = AnalysisPipeline()
