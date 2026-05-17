from __future__ import annotations

import json
import logging
import os
import uuid
from dataclasses import dataclass
from datetime import datetime, timezone
from typing import Any, Optional

from sqlalchemy.orm import Session

from app.db import crud
from app.models.analysis import AnalysisResponse, ExcludedCandidate
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
    penalty_path_service,
    risk_rule_service,
    situation_frame_service,
    situation_assessment_service,
    sr_lookup_service,
)
from app.services.hazard_normalizer import normalize_risk_feature_candidates
from app.services.industry_context import infer_industry_context
from app.utils.taxonomy import get_feature_label


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

        preliminary_guide_rows = guide_recommendation_service.get_standard_guides(
            db,
            sr_ids,
            direct_sr_ids=direct_sr_ids,
            limit=6,
            industry_contexts=industry_context.active_industries,
            risk_features=recommendation_risk_features,
            she_matches=recommendation_matches,
            visual_cues=visual_cues,
            context_text=" ".join(filter(None, [declared_industry_text, context_text])),
            situation_frame=situation_frame,
            apply_photo_top_gate=False,
            allow_support_without_observable_cue=observable_violation_signal,
        )
        preferred_guide_codes = self._unique(
            [row.get("guide_code") for row in preliminary_guide_rows if row.get("guide_code")]
        )
        checklist_rows = guide_recommendation_service.get_immediate_checklist_items(
            db,
            sr_ids,
            direct_sr_ids=direct_sr_ids,
            limit=12,
            risk_features=recommendation_risk_features,
            she_matches=recommendation_matches,
            visual_cues=visual_cues,
            industry_contexts=industry_context.active_industries,
            context_text=" ".join(filter(None, [declared_industry_text, context_text])),
            preferred_guide_codes=preferred_guide_codes,
            situation_frame=situation_frame,
            allow_contextual_ci_fallback=observable_violation_signal,
        )
        guide_rows = guide_recommendation_service.get_standard_guides(
            db,
            sr_ids,
            direct_sr_ids=direct_sr_ids,
            limit=6,
            industry_contexts=industry_context.active_industries,
            risk_features=recommendation_risk_features,
            she_matches=recommendation_matches,
            visual_cues=visual_cues,
            context_text=" ".join(filter(None, [declared_industry_text, context_text])),
            situation_frame=situation_frame,
            allow_support_without_observable_cue=observable_violation_signal,
        )
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
                )
            )
        return procedures

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
        """
        mode = os.environ.get("LLM_RERANK_MODE", "off").lower()
        if mode not in ("shadow", "active"):
            return []
        if not knowledge.guide_rows:
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

        try:
            self._append_analysis_log(
                scene_hash=scene_hash,
                mode=mode,
                industry=industry,
                visual_obs=visual_obs_texts,
                candidate_codes=candidate_codes,
                filter_result=filter_result,
                excluded=excluded,
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
    ) -> None:
        """Phase C.1 — append per-analysis log for self-refine mining.

        env LLM_RERANK_MODE=shadow|active 일 때만 기록. off에서는 skip.
        """
        if mode not in ("shadow", "active"):
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
        entry = {
            "ts": datetime.now(timezone.utc).isoformat(),
            "mode": mode,
            "scene_hash": scene_hash,
            "industry": industry,
            "visual_obs_count": len(visual_obs),
            "candidate_count": len(candidate_codes),
            "filter_keep": len(filter_result.keep),
            "filter_gray": len(filter_result.gray),
            "filter_drop": len(filter_result.drop),
            "excluded": [
                {
                    "guide_code": e.guide_code,
                    "source": e.source,
                    "reason": e.reason[:100],
                    "similarity": e.similarity,
                }
                for e in excluded
            ],
        }
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
    ) -> str:
        if finding_status == "confirmed" and any(obs.severity == "HIGH" for obs in observations):
            return "high"
        if finding_status in {"confirmed", "suspected"}:
            return "medium"
        return "low"

    def _summary(
        self,
        observations: list[VisualObservation],
        findings: list[Finding],
        penalty_paths: list[PenaltyPath],
    ) -> str:
        if findings:
            penalty_text = " 벌칙 안내 경로가 있습니다." if penalty_paths else ""
            return f"{findings[0].summary}{penalty_text}"
        if observations:
            return observations[0].text
        return "사진 또는 설명에서 확정 가능한 위험 단서를 찾지 못했습니다."

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
