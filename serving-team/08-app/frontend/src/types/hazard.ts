// WS-SAFETY-1/4: 'unknown' = 평가 못 함/근거 부족. 'low'(녹색 안전)와 구조적으로 분리해
// '미탐지 = 안전' 오신호를 차단한다(중립색·'판정 불가' 라벨).
export type RiskLevel = 'critical' | 'high' | 'medium' | 'low' | 'unknown';

export const riskLevelLabels: Record<RiskLevel, string> = {
  critical: '즉시 중지 필요',
  high: '높음',
  medium: '주의',
  low: '낮음',
  unknown: '판정 불가',
};

export const riskLevelColors: Record<RiskLevel, string> = {
  critical: 'risk-critical',
  high: 'risk-high',
  medium: 'risk-medium',
  low: 'risk-low',
  unknown: 'risk-unknown',
};
