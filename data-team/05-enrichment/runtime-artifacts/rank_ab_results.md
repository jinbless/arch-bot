=== RANK A/B (gold 129장 · y-코드 162 · reps 4 · gpt-5.4) ===
제외 0장(후보구성 129) · RANK 실패 0건 {'A': 0, 'B': 0, 'C': 0} · RESOLVE 실패 0건 · 후보밖코드 {'A': 16, 'B': 24, 'C': 11}

⚠ arm C(EXPERT_HINT)는 본 gold 129장을 본 뒤 작성된 규칙이다. 타임라인: gold 라벨링 → 동일 129장 조문별 오류분석(cuepool-candidate-ceiling-ab) → SSOT 규칙 커밋 9c322b4 → 본 하네스. 홀드아웃 분할 없음. 힌트가 명시 지목한 조문이 gold y의 약 53%를 덮고, 억제 대상 제3·5·38·39·40조는 gold y-count 0. 따라서 B->C / A->C Δ는 일반화 이득이 아니라 상한 추정치이며 bootstrap CI가 이 자유도를 잡지 못한다. 채택 판단은 A->B만 사용한다.

arm                  P@1   Hit@3   Hit@5     R@5     MRR      천장     후보
A base_plain       0.432   0.609   0.680   0.611   0.531   0.837   30.5
B union_plain      0.438   0.655   0.713   0.654   0.557   0.930   46.1
C union_expert     0.444   0.638   0.700   0.645   0.551   0.930   46.1

[A->B] p1 Δ+0.006 CI[-0.039,+0.054] non_inferior · hit3 Δ+0.046 CI[+0.000,+0.101] non_inferior · hit5 Δ+0.033 CI[-0.021,+0.091] non_inferior · mrr Δ+0.026 CI[-0.015,+0.074] non_inferior
[B->C] p1 Δ+0.006 CI[-0.043,+0.056] non_inferior · hit3 Δ-0.017 CI[-0.058,+0.021] inconclusive · hit5 Δ-0.014 CI[-0.054,+0.027] inconclusive · mrr Δ-0.006 CI[-0.038,+0.028] non_inferior  ⚠상한추정
[A->C] p1 Δ+0.012 CI[-0.054,+0.081] inconclusive · hit3 Δ+0.029 CI[-0.027,+0.091] non_inferior · hit5 Δ+0.019 CI[-0.043,+0.085] non_inferior · mrr Δ+0.021 CI[-0.031,+0.078] non_inferior  ⚠상한추정

[A->B] MDE80 p1 0.066(불일치 0.16) · hit3 0.071(불일치 0.21) · hit5 0.078(불일치 0.21) · mrr 0.063(불일치 0.46)
[B->C] MDE80 p1 0.071(불일치 0.19) · hit3 0.056(불일치 0.23) · hit5 0.060(불일치 0.23) · mrr 0.048(불일치 0.49)
[A->C] MDE80 p1 0.097(불일치 0.26) · hit3 0.084(불일치 0.29) · hit5 0.091(불일치 0.29) · mrr 0.077(불일치 0.54)

[상수 기저선(무LLM) — arm 절대치는 이 대비 순증으로 읽을 것]
baseline             P@1   Hit@3   Hit@5     R@5     MRR
const_제43조         0.302   0.302   0.364   0.336   0.354
cand_order         0.000   0.116   0.124   0.090   0.101
random_perm        0.039   0.109   0.147   0.106   0.126

[CROSS 상수 16조] gold y-mass 0.543 · gold전부CROSS내 60장 · CROSS로만 포착 65장
  출처: label_sheet.csv(8장·y 20건, 2026-06-21) y라벨 + 빈출 후보 큐레이션. 129장 curation gold와 다른 라벨링 회차이나 사진 중복 여부 미확인
  주: CROSS는 전 arm 공통 상수 → 페어드 Δ는 무편향. 영향은 절대수준 해석에 한정.

[유효성 게이트]
  PASS  G1_no_failure: {"n_rank_fail": 0, "n_dropped": 0}
  PASS  G2_order_not_dominant: {"max_abs": 0.0426, "by_arm": {"A": -0.0426, "B": 0.0155, "C": 0.0116}}
  PASS  G3_ceiling_reproduced: {"detail": []}
  PASS  G4_beats_constant: {"arm_p1": 0.432, "const_p1": 0.302}

[headroom 서브그룹] 12장 (A 놓침·B 포착 = 이득 유일경로, 탐색적)
  A base_plain     P@1 0.000 · Hit@3 0.000 · Hit@5 0.000 · MRR 0.000
  B union_plain    P@1 0.542 · Hit@3 0.729 · Hit@5 0.812 · MRR 0.655
  C union_expert   P@1 0.583 · Hit@3 0.792 · Hit@5 0.854 · MRR 0.680

[판정프레임] 주지표=A->B의 P@1. 사전지정 비열등 마진 -0.05. 판정 사다리: CI하한>0 gain / >마진 non_inferior / CI상한<0 harm / else inconclusive.
[해석 한계] n=129 · 이득경로 12장(최대 +9.3pt) · MDE80 0.066 → 이 설계는 **해악 검출용**이다. Δ가 0 근처인 것은 '이득 없음'이 아니라 '이 표본으로는 이득을 볼 수 없음'이다.
  arm 절대값은 상수 기저선 대비 순증으로만 읽고, 배포 성능 주장에 쓰지 않는다(태그·순서 중립화로 배포와 다름).