import React, { useEffect } from 'react';
import { Link, useParams } from 'react-router-dom';
import { analysisApi } from '../api/analysisApi';
import Loading from '../components/common/Loading';
import ErrorMessage from '../components/common/ErrorMessage';
import FindingsCard from '../components/results/FindingsCard';
import ImmediateActionsPanel from '../components/results/ImmediateActionsPanel';
import OwnerResourcesCard from '../components/results/OwnerResourcesCard';
import WorkFlowPanel from '../components/results/WorkFlowPanel';
import { useAnalysisStore } from '../store';
import type { AiActionAlignment, AnalysisResponse } from '../types/analysis';

/* 결과 화면 = 감독관 컨설팅 서사 3단계 (2026-08-09 2차 재설계).
 *
 *   1 사진에서 본 것          — AI 서술 (판정 아님)
 *   2 원래 이렇게 관리        — 기인물 앵커 흐름 6칸 ★ 화면의 주인공.
 *                              '지금 당장'(흐름 조문에서 선별한 즉시조치)과 'AI 제안 대조'를
 *                              같은 카테고리 안에 통합 — 즉시조치는 흐름 조문의 부분집합이므로
 *                              별도 패널로 두면 같은 조문이 두 번 나와 출처가 흐려진다.
 *   3 직접 확인할 자료        — 가이드·기본 안전수칙·안전검사
 *
 * 삭제(2026-08-09 사용자 결정): '사고가 나면'(벌칙 3경로)과 '분석 상세' 접힘 구역 —
 * "효과성이 없이 복잡하기만 하다". 백엔드 응답 필드는 유지(다른 소비자·기록 호환),
 * 화면에서만 내린다. legacy 갈래 계산 자체의 옵션화는 다음 작업.
 *
 * 흐름이 없으면(앵커 실패 ~35%) '지금 당장'이 기존 CI 폴백 패널로 독립해 2번 자리에 선다.
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

  // 조문 기반 즉시조치(rule:Article) → 흐름 패널의 '지금 당장' 스트립으로 들어간다.
  const statuteActions = analysis.immediate_actions.filter((a) => a.source_type === 'rule:Article');
  // 구 기록 호환: 정렬 필드가 없으면 즉시조치에 병기됐던 AI 제안을 '대조 전'으로 승계한다.
  const aiAlignments: AiActionAlignment[] = analysis.ai_action_alignments?.length
    ? analysis.ai_action_alignments
    : analysis.immediate_actions
        .filter((a) => a.source_type === 'app:VisualObservation')
        .map((a) => ({
          text: a.title,
          status: 'unaligned',
          matched_ref: '',
          matched_title: '',
          slot_key: '',
          slot_label: '',
          reason: '',
        }));
  const hasFlow = !!analysis.work_flow;
  // 텍스트 트랙 개통(2026-08-10): 텍스트 분석도 앵커→흐름을 타므로 사진 전제 문구를 분기한다
  const isText = analysis.analysis_type === 'text';
  const inputNoun = isText ? '서술' : '사진';
  // 앵커 정정 시 '지금 당장' 재선별의 순위 신호 — 분석 시점과 같은 사고형태 코드를 승계한다.
  // canonical 경로 ∪ hazard-직결 경로: 화재처럼 hazard 쪽에만 잡히는 축이 실측됐다(prod 5222 —
  // risk_features는 FALL뿐, hazards.mapped_codes에 FIRE_AND_EXPLOSION). 백엔드 선별과 같은 union
  // (analysis_pipeline._build_statute_actions 호출부 참조).
  const accidentCodes = Array.from(
    new Set([
      ...analysis.risk_features.filter((f) => f.axis === 'accident_type').map((f) => f.code),
      ...(analysis.hazards ?? []).flatMap((h) =>
        (h.mapped_codes ?? [])
          .filter((c) => c.startsWith('accident_type.'))
          .map((c) => c.slice('accident_type.'.length))
      ),
    ])
  );
  // 조문 선별이 흐름 스트립으로 들어갈 수 없을 때만 독립 패널을 보여준다(무회귀).
  // (조문 선별은 흐름에서만 나오지만, 흐름 없는 구 기록을 방어한다 — 즉시조치가 증발하면 안 된다)
  const showFallbackActions =
    (statuteActions.length === 0 || !hasFlow) && analysis.immediate_actions.length > 0;
  const nActions = showFallbackActions ? 2 : 0;
  const nFlow = hasFlow ? (nActions ? 3 : 2) : 0;
  const nResources = Math.max(nFlow, nActions, 1) + 1;

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

      {/* B0: 진입 게이트(Ada 응급 게이트 패턴) — 면책이 아니라 행동 지시. 이 한 줄이
          아래 전체를 '여유 있는 컨설팅 모드'로 재맥락화한다. 최상단 고정. */}
      <p className="rounded-lg bg-gray-900 px-3 py-2 text-[13px] font-medium text-white">
        ⛔ 지금 이 자리에서 사람이 다칠 수 있는 상태라면 — 이 화면이 아니라{' '}
        <strong>즉시 작업 중지</strong>가 먼저입니다.
      </p>

      <StageHeading n={1} title={isText ? '서술에서 파악한 것' : '사진에서 본 것'} />
      <FindingsCard analysis={analysis} />

      {showFallbackActions && (
        <>
          <StageHeading n={nActions} title="지금 당장" />
          <ImmediateActionsPanel
            items={analysis.immediate_actions}
            findingStatus={analysis.finding_status}
          />
        </>
      )}

      {hasFlow && (
        <>
          <StageHeading
            n={nFlow}
            title={
              analysis.work_flow?.anchor.kind === '기인물없음'
                ? '이 현장이 늘 갖춰야 하는 것'
                : '이 기계·작업은 원래 이렇게 관리합니다'
            }
            sub={
              analysis.work_flow?.anchor.kind === '기인물없음'
                ? '위험이 장소·통행 환경에서 오는 경우 — 기본 안전수칙에서 관련 주제'
                : '검수 체계를 거친 자료 · ‘지금 당장’ 조치 포함'
            }
          />
          <WorkFlowPanel
            flow={analysis.work_flow}
            actNow={statuteActions}
            aiAlignments={aiAlignments}
            inputNoun={inputNoun}
            accidentCodes={accidentCodes}
          />
        </>
      )}

      <StageHeading n={nResources} title="직접 확인할 자료" />
      <OwnerResourcesCard analysis={analysis} flow={analysis.work_flow} />
    </div>
  );
};

export default ResultPage;
