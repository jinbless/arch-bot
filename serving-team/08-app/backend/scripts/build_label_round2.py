# -*- coding: utf-8 -*-
"""2차 라벨 확장 세트 생성 — 미판정 코드를 감독관이 y/n 판정할 수 있게.

측정 문제: arm B top1 129장 중 51장(40%)이 '큐레이터가 판정한 적 없는 코드' → 오답인지 미판정인지 구분 불가.
해결: 각 사진의 {A/B/C rep0 top3 합집합 ∪ (추락 사진이면 형제 10종)} − 이미 판정된 코드 를 2차 판정 대상으로.

산출:
  real-test-photo/label_photo/label_round2.csv          (label_curation_gold.csv와 동일 스키마, match 빈칸)
  real-test-photo/label_photo/curation_viewer_r2.html   (블라인드 뷰어: 사진+후보, y/n/m, CSV 내보내기)
블라인드 원칙: 모델/arm 출처 비표기, 후보 순서 사진별 고정seed 무작위화, 기판정 코드는 회색 참고표시(재판정 불가).
재생성 안전: 판정은 localStorage(사진|조문 키)에 저장되므로 HTML 재생성해도 기존 판정 보존.
2026-07-30: 감독관 검수로 형제 세트에 제23조(가설통로)·제24조(사다리식 통로) 추가 + gold '조' 누락 정규화 + 안정 seed(md5).
"""
import csv, hashlib, json, random, re
from pathlib import Path

REPO = Path(__file__).resolve().parents[4]
ART = REPO / "data-team/05-enrichment/runtime-artifacts"
LP = REPO / "real-test-photo/label_photo"
GOLD = LP / "label_curation_gold.csv"
OUT_CSV = LP / "label_round2.csv"
OUT_HTML = LP / "curation_viewer_r2.html"

# 추락 형제 세트 — 감독관 검수(2026-07-30)로 사다리식 통로 제24조·가설통로 제23조 포함
SIB = ["제13조", "제23조", "제24조", "제30조", "제42조", "제43조", "제44조", "제45조", "제56조", "제68조"]


def norm_code(c):
    """gold CSV '조' 누락 오기 정규화(제45→제45조) — 미정규화 시 채점·중복제거에서 영영 미매칭."""
    c = (c or "").strip()
    m = re.fullmatch(r"제(\d+)(조(의\d+)?)?", c)
    if m and not m.group(2):
        return f"제{m.group(1)}조"
    return c


# 기판정
judged, pjts, ognl = {}, {}, {}
with GOLD.open(encoding="utf-8-sig") as f:
    for r in csv.DictReader(f):
        pf = r["photo_file"]
        m = (r.get("match") or "").strip().lower()
        judged.setdefault(pf, {})[norm_code(r["article_code"])] = m or "(빈칸)"
        pjts[pf] = r.get("pjts_id", "")
        ognl[pf] = r.get("ognl", "")

res = json.loads((ART / "rank_ab_results.json").read_text(encoding="utf-8"))
pp = res["per_photo"]
sig = {json.loads(l)["article_code"]: json.loads(l)
       for l in (ART / "article_signatures.jsonl").read_text(encoding="utf-8").splitlines() if l.strip()}
RULE = json.loads((REPO / "data-team/02-extraction/pipe-A/data/article-texts.json").read_text(encoding="utf-8"))["laws"]["RULE"]

rows, viewdata = [], []
for pf in sorted(pp):
    top = []
    for arm in ("A", "B", "C"):
        top += (pp[pf].get(arm, {}).get("top5") or [])[:3]
    jd = judged.get(pf, {})
    # 추락 사진 판정: 기판정 or top3에 형제조문 포함
    is_fall = bool(set(jd) & set(SIB)) or bool(set(top) & set(SIB))
    cand = list(dict.fromkeys(top + (SIB if is_fall else [])))
    new = [c for c in cand if c not in jd]
    if not new:
        continue
    # 안정 seed(md5) — 내장 hash()는 프로세스마다 달라 재생성 시 순서가 바뀜
    rnd = random.Random(int(hashlib.md5(pf.encode("utf-8")).hexdigest()[:8], 16))
    rnd.shuffle(new)
    for c in new:
        rows.append({"row": len(rows) + 1, "pjts_id": pjts.get(pf, ""), "photo_file": pf,
                     "ognl": ognl.get(pf, ""), "article_code": c,
                     "article_title": (sig.get(c, {}).get("title") or RULE.get(c, {}).get("title") or "(미보유)"),
                     "observable": sig.get(c, {}).get("observable", "?"), "source": "round2", "match": ""})
    viewdata.append({
        "file": pf, "pjts": pjts.get(pf, ""), "ognl": ognl.get(pf, ""),
        "new": [{"code": c,
                 "title": (sig.get(c, {}).get("title") or RULE.get(c, {}).get("title") or "(미보유)"),
                 "obs": sig.get(c, {}).get("observable", "?"),
                 "txt": (RULE.get(c, {}).get("fullText", "") or "")[:220]} for c in new],
        "old": [{"code": c, "v": v} for c, v in sorted(jd.items())],
    })

with OUT_CSV.open("w", encoding="utf-8-sig", newline="") as f:
    w = csv.DictWriter(f, fieldnames=["row", "pjts_id", "photo_file", "ognl", "article_code",
                                      "article_title", "observable", "source", "match"])
    w.writeheader(); w.writerows(rows)

TPL = """<!doctype html><html lang=ko><head><meta charset=utf-8>
<meta name=viewport content="width=device-width,initial-scale=1"><title>2차 검수 — 미판정 조문 y/n</title>
<style>
*{box-sizing:border-box}body{margin:0;font:14px/1.55 -apple-system,Segoe UI,'Malgun Gothic',sans-serif;background:#f6f7f9;color:#111}
header{position:sticky;top:0;background:#fff;border-bottom:1px solid #dcdfe4;padding:9px 14px;z-index:20;display:flex;gap:8px;align-items:center;flex-wrap:wrap}
h1{font-size:15px;margin:0 10px 0 0}
button{padding:5px 11px;border:1px solid #c8ccd2;background:#fff;border-radius:6px;cursor:pointer;font-size:13px}
button.pri{background:#2563eb;color:#fff;border-color:#2563eb}
#prog{font-size:12px;color:#555;margin-left:auto}
.card{background:#fff;border:1px solid #dcdfe4;border-radius:10px;margin:12px;padding:12px;display:grid;grid-template-columns:minmax(280px,42%) 1fr;gap:14px}
@media(max-width:900px){.card{grid-template-columns:1fr}}
.card.done{opacity:.5}
img{width:100%;border-radius:8px;background:#000;image-orientation:from-image}
.meta{font-size:12px;color:#666;margin-bottom:6px;word-break:break-all}
table{width:100%;border-collapse:collapse;font-size:13px}
td,th{border-bottom:1px solid #eceef1;padding:5px 6px;vertical-align:top;text-align:left}
th{font-size:11px;color:#666;font-weight:600}
.code{font-weight:700;white-space:nowrap}
.txt{color:#555;font-size:12px}
.b{display:flex;gap:4px}
.b button{padding:3px 9px;font-size:12px}
.b button.on[data-v=y]{background:#16a34a;color:#fff;border-color:#16a34a}
.b button.on[data-v=n]{background:#dc2626;color:#fff;border-color:#dc2626}
.b button.on[data-v=m]{background:#d97706;color:#fff;border-color:#d97706}
.old{font-size:11px;color:#8a8f98;margin-top:8px;border-top:1px dashed #dcdfe4;padding-top:6px}
.old b{color:#6b7280}
.obs{font-size:10px;padding:1px 5px;border-radius:8px;background:#eef1f4;color:#555}
</style></head><body>
<header><h1>2차 검수 — 미판정 조문 y/n</h1>
<button class="pri" onclick="ex()">CSV 내보내기</button>
<button onclick="tog()" id="fb">미검토만 보기</button>
<button onclick="nx()">다음 미검토 ↓</button>
<span id=prog></span></header>
<div id=root></div>
<script>
const DATA=__DATA__;
const KEY='label_r2_v1';
let S=JSON.parse(localStorage.getItem(KEY)||'{}');
let onlyTodo=false;
function save(){localStorage.setItem(KEY,JSON.stringify(S));prog();}
function prog(){let t=0,d=0;DATA.forEach(p=>p.new.forEach(c=>{t++;if(S[p.file+'|'+c.code])d++;}));
 document.getElementById('prog').textContent=`판정 ${d} / ${t} (${(100*d/t||0).toFixed(0)}%)`;
 DATA.forEach((p,i)=>{const el=document.getElementById('c'+i);if(!el)return;
  const done=p.new.every(c=>S[p.file+'|'+c.code]);el.classList.toggle('done',done);
  if(onlyTodo)el.style.display=done?'none':'';else el.style.display='';});}
function set(f,c,v){const k=f+'|'+c;S[k]=(S[k]===v?undefined:v);if(!S[k])delete S[k];save();
 document.querySelectorAll(`[data-k="${CSS.escape(k)}"] button`).forEach(b=>b.classList.toggle('on',b.dataset.v===S[k]));}
function tog(){onlyTodo=!onlyTodo;document.getElementById('fb').textContent=onlyTodo?'전체 보기':'미검토만 보기';prog();}
function nx(){const el=[...document.querySelectorAll('.card')].find(e=>!e.classList.contains('done'));
 if(el)el.scrollIntoView({behavior:'smooth',block:'start'});}
function ex(){let out='row,pjts_id,photo_file,ognl,article_code,article_title,observable,source,match\\n',i=0;
 const q=s=>'"'+String(s==null?'':s).replace(/"/g,'""')+'"';
 DATA.forEach(p=>p.new.forEach(c=>{i++;out+=[i,q(p.pjts),q(p.file),q(p.ognl),q(c.code),q(c.title),q(c.obs),'round2',q(S[p.file+'|'+c.code]||'')].join(',')+'\\n';}));
 const b=new Blob(['\\ufeff'+out],{type:'text/csv;charset=utf-8'}),a=document.createElement('a');
 a.href=URL.createObjectURL(b);a.download='label_round2_filled.csv';a.click();}
document.getElementById('root').innerHTML=DATA.map((p,i)=>`
<div class=card id=c${i}><div><img loading=lazy src="${encodeURI(p.file)}" alt=""></div><div>
<div class=meta>${p.file}<br>감독건 ${p.pjts}</div>
<table><tr><th>조문</th><th>내용</th><th>판정</th></tr>
${p.new.map(c=>`<tr><td class=code>${c.code}<br><span class=obs>${c.obs}</span></td>
<td>${c.title}<div class=txt>${c.txt.replace(/</g,'&lt;')}</div></td>
<td><div class=b data-k="${p.file}|${c.code}">
<button data-v=y onclick="set('${p.file.replace(/'/g,"\\\\'")}','${c.code}','y')">y</button>
<button data-v=n onclick="set('${p.file.replace(/'/g,"\\\\'")}','${c.code}','n')">n</button>
<button data-v=m onclick="set('${p.file.replace(/'/g,"\\\\'")}','${c.code}','m')">m</button>
</div></td></tr>`).join('')}
</table>
<div class=old><b>1차 판정(참고·수정불가)</b> ${p.old.map(o=>o.code+':'+o.v).join(' · ')||'—'}</div>
</div></div>`).join('');
document.querySelectorAll('.b').forEach(d=>{const k=d.dataset.k;
 d.querySelectorAll('button').forEach(b=>b.classList.toggle('on',b.dataset.v===S[k]));});
prog();
</script></body></html>"""

OUT_HTML.write_text(TPL.replace("__DATA__", json.dumps(viewdata, ensure_ascii=False)), encoding="utf-8")

nph = len(viewdata)
npair = len(rows)
sib_new = sum(1 for r in rows if r["article_code"] in SIB)
print(f"2차 판정 대상: {npair}쌍 · {nph}장 (사진당 평균 {npair/max(nph,1):.1f}, 최대 {max(len(v['new']) for v in viewdata)})")
print(f"  그중 형제조문 {sib_new}건")
print(f"→ {OUT_CSV.name} · {OUT_HTML.name}")
