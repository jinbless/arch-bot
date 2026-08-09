import React, { useEffect } from 'react';
import { Link, useParams } from 'react-router-dom';
import { analysisApi } from '../api/analysisApi';
import Loading from '../components/common/Loading';
import ErrorMessage from '../components/common/ErrorMessage';
import ArticleCandidatesPanel from '../components/results/ArticleCandidatesPanel';
import FindingsCard from '../components/results/FindingsCard';
import GuideProcedurePanel from '../components/results/GuideProcedurePanel';
import HazardGuideRelationsPanel from '../components/results/HazardGuideRelationsPanel';
import ImmediateActionsPanel from '../components/results/ImmediateActionsPanel';
import OwnerResourcesCard from '../components/results/OwnerResourcesCard';
import PenaltyPathPanel from '../components/results/PenaltyPathPanel';
import ReasoningTracePanel from '../components/results/ReasoningTracePanel';
import RiskOverviewPanel from '../components/results/RiskOverviewPanel';
import WorkFlowPanel from '../components/results/WorkFlowPanel';
import { useAnalysisStore } from '../store';
import type { AnalysisResponse } from '../types/analysis';

/* 결과 화면 = 감독관 컨설팅 서사 5단계 (2026-08 재설계).
 *
 *   1 사진에서 본 것   — AI 서술 (판정 아님)
 *   2 지금 당장        — 즉시 조치
 *   3 원래 이렇게 관리 — 기인물 앵커 흐름 6칸 ★ 검수 완료된 화면의 주인공
 *   4 직접 확인할 자료 — 가이드·기본 안전수칙·안전검사
 *   5 사고가 나면      — 벌칙 3경로
 *
 * 정확도 미검증 경로(정규화·SHE·표준절차·조문후보)는 '분석 상세'로 접는다 —
 * 지우는 게 아니라 사업주 첫 화면에서 내리는 것이다. 근거 추적은 계속 가능해야 한다.
 */

const StageHeading: React.FC<{ n: number; title: string; sub?: string }> = ({ n, title, sub }) => (
  <div className="flex items-baseline gap-2 mt-2">
    <span className="flex-none w-6 h-6 rounded-full bg-gray-900 text-white text-sm font-bold flex items-center justify-center">
      {n}
    </span>
    <h2 className="text-base font-bold text-gray-900">{title}</h2>
    {sub && <span className="text-xs text-gray-500">{sub}</span>}
  </div>
);

const ResultPage: React.FC = () => {
  const { id } = useParams<{ id: string }>();
  const { currentAnalysis, setCurrentAnalysis, isLoading, error, setLoading, setError } =
    useAnalysisStore();

  useEffect(() => {
    const fetchAnalysis = async () => {
      if (!id || currentAnalysis?.analysis_id === id) return;
      setLoading(true);
      try {
        const result = await analysisApi.getAnalysis(id);
        setCurrentAnalysis(result);
      } catch (err) {
        setError(err instanceof Error ? err.message : '분석 결과를 불러오지 못했습니다.');
      } finally {
        setLoading(false);
      }
    };
    fetchAnalysis();
  }, [id, currentAnalysis?.analysis_id, setCurrentAnalysis, setLoading, setError]);

  if (isLoading) return <Loading message="분석 결과를 불러오는 중..." />;

  if (error) {
    return (
      <div className="max-w-2xl mx-auto">
        <ErrorMessage message={error} />
        <div className="mt-4 text-center">
          <Link to="/analysis" className="text-primary-600 hover:text-primary-800">
            새 분석 시작하기
          </Link>
        </div>
      </div>
    );
  }

  if (!currentAnalysis) {
    return (
      <div className="text-center py-12">
        <p className="text-gray-500">분석 결과를 찾을 수 없습니다.</p>
        <Link to="/analysis" className="text-primary-600 hover:text-primary-800 mt-4 inline-block">
          새 분석 시작하기
        </Link>
      </div>
    );
  }

  const analysis = currentAnalysis as AnalysisResponse;

  return (
    <div className="max-w-5xl mx-auto space-y-4">
      <div className="flex items-center justify-between">
        <Link to="/analysis" className="text-gray-600 hover:text-gray-800">
          새 분석
        </Link>
        <Link to="/history" className="text-primary-600 hover:text-primary-800">
          분석 기록 보기
        </Link>
      </div>

      <StageHeading n={1} title="사진에서 본 것" />
      <FindingsCard analysis={analysis} />

      <StageHeading n={2} title="지금 당장" />
      <ImmediateActionsPanel
        items={analysis.immediate_actions}
        findingStatus={analysis.finding_status}
      />

      {analysis.work_flow && (
        <>
          <StageHeading n={3} title="이 기계·작업은 원래 이렇게 관리합니다" sub="사람 검수를 마친 자료" />
          <WorkFlowPanel flow={analysis.work_flow} />
        </>
      )}

      <StageHeading n={analysis.work_flow ? 4 : 3} title="직접 확인할 자료" />
      <OwnerResourcesCard analysis={analysis} flow={analysis.work_flow} />

      <StageHeading n={analysis.work_flow ? 5 : 4} title="사고가 나면" sub="위반 상태에서 사고 시 처벌 경로" />
      <PenaltyPathPanel paths={analysis.penalty_paths} />

      <details className="bg-gray-50 rounded-xl border border-gray-200 p-4">
        <summary className="cursor-pointer text-sm font-semibold text-gray-600 select-none">
          분석 상세 · 근거 보기 (정규화 특징, SHE 패턴, 위험요소별 가이드, 표준절차, 조문 후보)
        </summary>
        <div className="mt-4 space-y-4">
          <RiskOverviewPanel analysis={analysis} />
          <HazardGuideRelationsPanel analysis={analysis} />
          <GuideProcedurePanel procedures={analysis.standard_procedures} />
          <ArticleCandidatesPanel
            candidates={analysis.article_candidates}
            findingStatus={analysis.finding_status}
          />
          <ReasoningTracePanel
            trace={analysis.reasoning_trace}
            matches={analysis.situation_matches.length}
          />
        </div>
      </details>
    </div>
  );
};

export default ResultPage;
