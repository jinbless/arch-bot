import { apiClient } from './index';
import type { WorkFlow } from '../types/analysis';

/**
 * 앵커 정정용 흐름 조회.
 *
 * 두 호출 모두 LLM을 쓰지 않는다(로드된 흐름 데이터 조회만) — 사용자가 기인물을 몇 번 바꿔도 비용이 없다.
 * 플래그가 off면 백엔드가 404를 준다(호출부에서 조용히 무시).
 */

export interface FlowGroup {
  group_key: string;
  label: string;
  path: string;
  is_inspection_target: boolean;
  /** 기인물 | 장소 | 환경 | 부적격. 부적격은 규칙 편제상의 칸이라 사진으로 지목할 수 없다 */
  kind?: string;
  n_items: number;
}

/** 사진과 무관하게 늘 지켜야 하는 것 — 흐름과 달리 앵커에 매달리지 않는다 */
export interface AlwaysItem {
  text: string;
  ref: string;
  source: string;
  evidence?: string;
  tier: '법정' | '권고';
  group: string;
}

export interface AlwaysTopic {
  name: string;
  desc: string;
  n: number;
  items: AlwaysItem[];
}

export const flowApi = {
  /** 기본 안전수칙 — 앵커 정확도와 무관하게 항상 맞는 유일한 화면 */
  always: async (): Promise<{ topics: AlwaysTopic[]; n_total: number; reviewed: boolean }> => {
    const res = await apiClient.get<{ topics: AlwaysTopic[]; n_total: number; reviewed: boolean }>(
      '/flow/always'
    );
    return res.data;
  },

  /** 앵커 선택기용 전체 목록. 대안 칩만으로는 완전 오인식(26.7%)을 고칠 수 없다. */
  listGroups: async (): Promise<FlowGroup[]> => {
    const res = await apiClient.get<{ groups: FlowGroup[] }>('/flow/groups');
    return res.data.groups ?? [];
  },

  /** 지정한 기인물의 흐름 + '지금 당장' 재선별. alternates를 넘기면 되돌아갈 후보를 유지한다.
   *  accidentCodes(원래 분석의 사고형태)를 넘기면 재선별 순위가 분석 시점과 같은 신호를 쓴다. */
  byGroupKey: async (
    groupKey: string,
    opts?: { alternates?: string[]; fromGroupKey?: string; accidentCodes?: string[] }
  ): Promise<WorkFlow> => {
    // 쿼리를 직접 만든다. axios 기본 직렬화는 배열을 `alternate[]=`로 내보내 FastAPI가 못 읽고,
    // 콤마로 이어붙이면 그룹키 자체에 콤마가 있는 경우('관리감독자의 직무, 사용의 제한 등')가 깨진다.
    const qs = new URLSearchParams();
    qs.append('group_key', groupKey);
    (opts?.alternates ?? []).forEach((a) => qs.append('alternate', a));
    if (opts?.fromGroupKey) qs.append('from_group_key', opts.fromGroupKey);
    (opts?.accidentCodes ?? []).forEach((c) => qs.append('accident_code', c));
    const res = await apiClient.get<WorkFlow>(`/flow?${qs.toString()}`);
    return res.data;
  },
};
