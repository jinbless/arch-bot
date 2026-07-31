=== RANK A/B v2 (gold v2 · 129장 · y 195 · reps 4) ===
실패 0 · 제외 0 · 후보밖코드 {'A': 31, 'B': 28}

arm                P@1   Hit@3   Hit@5     R@5     MRR   (v1-gold P@1)
A baseline       0.475   0.663   0.723   0.625   0.577   (0.419)
B union          0.521   0.734   0.814   0.704   0.638   (0.455)
D promote-1      0.523   0.723   0.783   0.680   0.630   (0.459)
const_제43조       0.326   0.326   0.403   0.313   0.379

[A->B] p1 Δ+0.046 CI[+0.002,+0.095] · hit3 Δ+0.072 CI[+0.019,+0.128] · hit5 Δ+0.091 CI[+0.039,+0.147]
[A->D] p1 Δ+0.048 CI[+0.010,+0.093] · hit3 Δ+0.060 CI[+0.023,+0.103] · hit5 Δ+0.060 CI[+0.023,+0.103]
[B->D] p1 Δ+0.002 CI[-0.019,+0.021] · hit3 Δ-0.012 CI[-0.046,+0.021] · hit5 Δ-0.031 CI[-0.066,+0.004]

[계층판정] H1 비headroom A→D Δ-0.0129 CI[-0.0280,-0.0022] (마진 -0.02) → FAIL
          H2 headroom(n=13) A→D Δ+0.5962 CI[+0.3462,+0.8462] → FAIL
          verdict: D_rejected

[층화] CROSS밖(n=50) A→B Δ+0.150 / CROSS안(n=79) Δ-0.019
[유효성 게이트]
  PASS  G1_no_failure: {"n_fail": 0, "n_dropped": 0}
  PASS  G2_order: {"max_abs": 0.0194, "by_arm": {"A": -0.0194, "B": 0.0039, "D": 0.0}}
  PASS  G3_ceiling_v1_reproduced: {"detail": []}
  PASS  G4_beats_const: {"A_p1": 0.475, "const_p1": 0.326}
  PASS  G5_full_ranked_saved: {}