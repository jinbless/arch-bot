#!/usr/bin/env python3
"""정식 FP 측정 — 블라인드 이진 검수 뷰어 생성 (사전등록: docs/dev-notes/fp-measurement-2026-08-01.md).

판정자는 **사진만** 본다. 파이프라인이 무엇을 주장했는지는 일절 싣지 않는다(anchoring 방지).
사진당 3택: 위반 있음 / 위반 없음 / 모호. 조문을 고르는 게 아니라 이진 판단만.

- 표본은 `fp_sample.json`(사전등록 고정)만 읽는다 — 뷰어가 표본을 다시 뽑지 않는다.
- 판정은 localStorage('fp_binary_v1')에 저장 → HTML을 다시 생성해도 보존.
- 원본이 장당 ~4MB(80장 350MB)라 그대로 띄우면 검수가 불가능하다 → **EXIF 회전 보정 + 축소 썸네일**을
  `fp_thumbs/`에 굽고 뷰어는 그것만 로드한다(판정에 필요한 해상도는 유지: 긴 변 1600px).
- 산출물은 전부 `real-test-photo/`(gitignore) 안에 둔다.

사용: python scripts/build_fp_viewer.py [--round 2]
서빙: .claude/launch.json의 fp-viewer(포트 8919) → http://127.0.0.1:8919/fp_viewer[_r2].html
"""
from __future__ import annotations

import argparse
import json
from pathlib import Path

from PIL import Image, ImageOps

ap = argparse.ArgumentParser()
ap.add_argument("--round", type=int, default=1, choices=(1, 2))
args = ap.parse_args()

HERE = Path(__file__).resolve()
REPO = HERE.parents[4]
POOL = REPO / "real-test-photo" / "no_label_photo"
ART = REPO / "data-team" / "05-enrichment" / "runtime-artifacts"
# 라운드별로 표본·썸네일·판정 저장소를 완전히 분리한다 — 섞이면 두 측정이 오염된다
SUFFIX = "" if args.round == 1 else f"_r{args.round}"
THUMBS = POOL / f"fp_thumbs{SUFFIX}"
SAMPLE = ART / f"fp_sample{SUFFIX}.json"
OUT_HTML = POOL / f"fp_viewer{SUFFIX}.html"
STORE_KEY = f"fp_binary{SUFFIX}_v1"
CSV_NAME = f"fp_binary_filled{SUFFIX}.csv"
MAX_SIDE = 1600

photos = json.loads(SAMPLE.read_text(encoding="utf-8"))["photos"]
missing = [p for p in photos if not (POOL / p).exists()]
if missing:
    raise SystemExit(f"표본 사진 {len(missing)}장이 없다: {missing[:3]}")

THUMBS.mkdir(exist_ok=True)
made = 0
for i, name in enumerate(photos):
    dst = THUMBS / f"{i:03d}.jpg"          # 한글·괄호 파일명 URL 인코딩 문제 회피
    if dst.exists():
        continue
    with Image.open(POOL / name) as im:
        im = ImageOps.exif_transpose(im).convert("RGB")   # 촬영 방향 확정(회전 오판 방지)
        im.thumbnail((MAX_SIDE, MAX_SIDE))
        im.save(dst, "JPEG", quality=82, optimize=True)
    made += 1
print(f"썸네일 {made}장 생성(기존 재사용 {len(photos) - made}) → {THUMBS.name}/")

TPL = """<!doctype html><html lang=ko><head><meta charset=utf-8>
<meta name=viewport content="width=device-width,initial-scale=1"><title>FP 검수 — 위반 유무 이진 판정</title>
<style>
*{box-sizing:border-box}body{margin:0;font:14px/1.55 -apple-system,Segoe UI,'Malgun Gothic',sans-serif;background:#f6f7f9;color:#111}
header{position:sticky;top:0;background:#fff;border-bottom:1px solid #dcdfe4;padding:9px 14px;z-index:20;display:flex;gap:8px;align-items:center;flex-wrap:wrap}
h1{font-size:15px;margin:0 10px 0 0}
button{padding:5px 11px;border:1px solid #c8ccd2;background:#fff;border-radius:6px;cursor:pointer;font-size:13px}
button.pri{background:#2563eb;color:#fff;border-color:#2563eb}
#prog{font-size:12px;color:#555;margin-left:auto}
.hint{font-size:12px;color:#6b7280;padding:6px 14px;background:#eef2f7;border-bottom:1px solid #dfe3e8}
.card{background:#fff;border:1px solid #dcdfe4;border-radius:10px;margin:12px;padding:12px}
.card.done{opacity:.5}
.card.cur{border-color:#2563eb;box-shadow:0 0 0 2px #bfdbfe}
img{width:100%;height:74vh;min-height:340px;object-fit:contain;border-radius:8px;background:#111}
.meta{font-size:11px;color:#8a9099;margin:6px 0;word-break:break-all}
.b{display:flex;gap:6px;flex-wrap:wrap;align-items:center;margin-top:6px}
.b button{padding:6px 14px;font-size:14px}
.b button.on[data-v=y]{background:#dc2626;color:#fff;border-color:#dc2626}
.b button.on[data-v=n]{background:#16a34a;color:#fff;border-color:#16a34a}
.b button.on[data-v=m]{background:#d97706;color:#fff;border-color:#d97706}
.memo{flex:1;min-width:180px;padding:5px 8px;border:1px solid #d6dae0;border-radius:6px;font-size:12px}
</style></head><body>
<header><h1>FP 검수 — 이 사진에 위반이 보이는가?</h1>
<button class="pri" onclick="ex()">CSV 내보내기</button>
<button onclick="tog()" id="fb">미판정만 보기</button>
<button onclick="nx()">다음 미판정 ↓</button>
<span id=prog></span></header>
<div class=hint>사진만 보고 <b>산업안전보건기준규칙 위반이 보이는지</b>만 판정합니다. 조문을 고를 필요 없습니다.
확실치 않으면 <b>모호</b>. 서류·절차 위반(교육·신호체계 등)은 사진으로 알 수 없으니 <b>위반 없음</b>이 아니라 <b>모호</b>로 두세요.
단축키 <b>1</b>=있음 <b>2</b>=없음 <b>3</b>=모호 (파란 테두리 카드에 적용, 자동으로 다음 장)</div>
<div id=root></div>
<script>
const DATA=__DATA__;
const KEY='__KEY__';
let S=JSON.parse(localStorage.getItem(KEY)||'{}');
let onlyTodo=false, cur=0;
function save(){localStorage.setItem(KEY,JSON.stringify(S));prog();}
function prog(){const d=DATA.filter(f=>S[f]&&S[f].v).length;
 const c={y:0,n:0,m:0};DATA.forEach(f=>{if(S[f]&&S[f].v)c[S[f].v]++;});
 document.getElementById('prog').textContent=`판정 ${d} / ${DATA.length} (${(100*d/DATA.length||0).toFixed(0)}%) · 있음 ${c.y} · 없음 ${c.n} · 모호 ${c.m}`;
 DATA.forEach((f,i)=>{const el=document.getElementById('c'+i);if(!el)return;
  const done=!!(S[f]&&S[f].v);el.classList.toggle('done',done);
  if(onlyTodo)el.style.display=done?'none':'';else el.style.display='';});}
function set(i,v){const f=DATA[i];const o=S[f]||{};
 o.v=(o.v===v?undefined:v);if(!o.v)delete o.v;S[f]=o;if(!o.v&&!o.memo)delete S[f];
 save();paint(i);if(o.v)setTimeout(()=>nx(),120);}
function memo(i,t){const f=DATA[i];const o=S[f]||{};o.memo=t;if(!o.memo&&!o.v)delete S[f];else S[f]=o;save();}
function paint(i){const f=DATA[i];const el=document.getElementById('c'+i);if(!el)return;
 el.querySelectorAll('.b button[data-v]').forEach(b=>b.classList.toggle('on',b.dataset.v===(S[f]||{}).v));}
function mark(i){document.querySelectorAll('.card').forEach(e=>e.classList.remove('cur'));
 const el=document.getElementById('c'+i);if(el){el.classList.add('cur');cur=i;}}
function nx(){for(let k=cur+1;k<DATA.length;k++){if(!(S[DATA[k]]||{}).v){go(k);return;}}
 for(let k=0;k<DATA.length;k++){if(!(S[DATA[k]]||{}).v){go(k);return;}}
 alert('모든 사진 판정 완료 — CSV 내보내기를 누르세요.');}
function go(i){mark(i);document.getElementById('c'+i).scrollIntoView({block:'start',behavior:'smooth'});}
function tog(){onlyTodo=!onlyTodo;document.getElementById('fb').textContent=onlyTodo?'전체 보기':'미판정만 보기';prog();}
function ex(){const rows=[['photo_file','verdict','memo']];
 DATA.forEach(f=>{const o=S[f]||{};rows.push([f,o.v||'',(o.memo||'').replace(/[\\r\\n",]/g,' ')]);});
 const csv='\\ufeff'+rows.map(r=>r.map(x=>`"${String(x).replace(/"/g,'""')}"`).join(',')).join('\\r\\n');
 const a=document.createElement('a');a.href=URL.createObjectURL(new Blob([csv],{type:'text/csv'}));
 a.download='__CSV__';a.click();}
document.addEventListener('keydown',e=>{if(e.target.tagName==='INPUT')return;
 const m={'1':'y','2':'n','3':'m'};if(m[e.key]){e.preventDefault();set(cur,m[e.key]);}});
const root=document.getElementById('root');
root.innerHTML=DATA.map((f,i)=>`<div class=card id=c${i} onclick="mark(${i})">
 <img loading="${i<3?'eager':'lazy'}" decoding=async src="__THUMBS__/${String(i).padStart(3,'0')}.jpg" alt="">
 <div class=meta>#${i+1} · ${f.replace(/</g,'&lt;')}</div>
 <div class=b>
  <button data-v=y onclick="set(${i},'y')">위반 있음 (1)</button>
  <button data-v=n onclick="set(${i},'n')">위반 없음 (2)</button>
  <button data-v=m onclick="set(${i},'m')">모호 (3)</button>
  <input class=memo placeholder="메모(선택)" oninput="memo(${i},this.value)" value="${((S[f]||{}).memo||'').replace(/"/g,'&quot;')}">
 </div></div>`).join('');
DATA.forEach((f,i)=>paint(i));mark(0);prog();
</script></body></html>"""

OUT_HTML.write_text(TPL.replace("__DATA__", json.dumps(photos, ensure_ascii=False))
                       .replace("__KEY__", STORE_KEY).replace("__CSV__", CSV_NAME)
                       .replace("__THUMBS__", THUMBS.name), encoding="utf-8")
print(f"[round {args.round}] 표본 {len(photos)}장 → {OUT_HTML} (저장소 {STORE_KEY} · 내보내기 {CSV_NAME})")
print("서빙: .claude/launch.json 의 fp-viewer(8919) → http://127.0.0.1:8919/fp_viewer.html")
