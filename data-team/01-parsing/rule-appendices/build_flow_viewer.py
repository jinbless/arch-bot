#!/usr/bin/env python3
"""흐름 라벨 검수 뷰어 생성 — 검수 도구이자 결과 화면 프로토타입.

두 가지를 한 물건으로 한다. 따로 만들면 같은 걸 두 번 만든다.
  ① 검수  — 704개 항목이 각각 맞는 단계에 있는지 사람이 판정한다
  ② 설계  — 사업주가 이 화면을 읽고 뭘 해야 하는지 아는지 본다

검수하는 오류 유형은 둘이다. 실제로 둘 다 나왔다:
  · 단계 오배치 — 제171조(전도 등의 방지)가 장면 문구 때문에 '인적 배치'로 갔다
  · 기인물 오부착 — 제41조(차량계 이탈)가 프레스에 붙었다(적용범위 무시)
그래서 판정 버튼이 '맞음 / 다른 칸 / 이 기인물과 무관 / 모호' 네 개다.

⚠ 단계에 번호를 매기지 않는다. '8단계 중 4단계'는 시간 추론이라 미측정 오류원이 된다.

사용: python data-team/01-parsing/rule-appendices/build_flow_viewer.py
출력: data-team/05-enrichment/runtime-artifacts/flow_review_viewer.html (자립형, 서버 불필요)
"""
from __future__ import annotations

import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[3]
ART = ROOT / "data-team" / "05-enrichment" / "runtime-artifacts"
SRC = ART / "flow_slice_all.json"
OUT = ART / "flow_review_viewer.html"

PHASES = [("PLAN", "계획·사전조사"), ("ASSIGN", "인적 배치·자격"), ("PRECHECK", "작업 시작 전 점검"),
          ("EXEC", "작업 중"), ("POST", "종료·이탈"), ("PERIODIC", "정기점검")]

CSS = """
:root{--bg:#0f1115;--panel:#171a21;--line:#272b35;--fg:#e6e8ee;--dim:#9aa1b1;
      --ok:#3fb950;--bad:#f85149;--move:#d29922;--vague:#8b949e;--law:#58a6ff;--rec:#a371f7}
*{box-sizing:border-box}
body{margin:0;font:14px/1.6 -apple-system,"Segoe UI","Malgun Gothic",sans-serif;background:var(--bg);color:var(--fg)}
header{position:sticky;top:0;z-index:9;background:var(--panel);border-bottom:1px solid var(--line);
       padding:10px 16px;display:flex;gap:16px;align-items:center;flex-wrap:wrap}
header h1{font-size:15px;margin:0;font-weight:600}
.bar{flex:1;min-width:160px;height:8px;background:#0b0d11;border-radius:4px;overflow:hidden}
.bar>i{display:block;height:100%;background:var(--ok);width:0;transition:width .2s}
button{font:inherit;color:var(--fg);background:#21262d;border:1px solid var(--line);
       border-radius:6px;padding:4px 10px;cursor:pointer}
button:hover{border-color:#3d444d}
.wrap{display:flex;align-items:flex-start}
aside{width:290px;flex:none;position:sticky;top:49px;max-height:calc(100vh - 49px);overflow:auto;
      border-right:1px solid var(--line);padding:8px}
aside div{padding:7px 9px;border-radius:6px;cursor:pointer;font-size:13px;display:flex;gap:8px;align-items:baseline}
aside div:hover{background:#1c2029}
aside div.on{background:#1f6feb33;outline:1px solid #1f6feb66}
aside .n{color:var(--dim);font-size:11px;margin-left:auto;flex:none;font-variant-numeric:tabular-nums}
aside .done{color:var(--ok)}
main{flex:1;padding:16px 20px;max-width:1000px}
h2{font-size:19px;margin:0 0 4px}
.meta{color:var(--dim);font-size:12px;margin-bottom:18px}
.meta b{color:var(--fg);font-weight:600}
section{margin-bottom:22px;border:1px solid var(--line);border-radius:10px;overflow:hidden}
section>h3{margin:0;padding:9px 13px;background:var(--panel);font-size:13px;font-weight:600;
           display:flex;gap:10px;align-items:center;border-bottom:1px solid var(--line)}
section>h3 .c{color:var(--dim);font-weight:400;font-size:12px}
section.empty>h3{opacity:.55}
.none{padding:12px 13px;color:var(--dim);font-size:13px}
.grp{padding:7px 13px;font-size:11px;letter-spacing:.04em;border-bottom:1px solid var(--line);background:#12151b}
.grp.law{color:var(--law)}.grp.rec{color:var(--rec)}
.item{padding:9px 13px;border-bottom:1px solid #1e222a;display:flex;gap:11px;align-items:flex-start}
.item:last-child{border-bottom:0}
.item .t{flex:1;min-width:0}
.item .t p{margin:0}
.item .src{font-size:11px;color:var(--dim);margin-top:3px}
/* 이 항목이 왜 이 칸에 있는지 — 조문 원문 문구. 검수자가 원문을 따로 찾아 읽지 않아도 되게 한다. */
.item .ev{font-size:12px;color:#b8c0d0;margin-top:4px;padding-left:9px;border-left:2px solid #2f3542}
.tag{display:inline-block;padding:0 6px;border-radius:4px;background:#21262d;border:1px solid var(--line);
     font-size:10.5px;color:var(--dim);margin-right:5px}
.tag.law{color:var(--law);border-color:#1f6feb55}.tag.rec{color:var(--rec);border-color:#a371f755}
.acts{display:flex;gap:4px;flex:none}
.acts button{padding:2px 8px;font-size:12px;min-width:30px}
.acts button.a{background:#21262d}
.item[data-v="ok"]{background:#3fb95012}.item[data-v="ok"] button[data-a="ok"]{background:var(--ok);color:#04260c;border-color:var(--ok)}
.item[data-v="move"]{background:#d2992212}.item[data-v="move"] button[data-a="move"]{background:var(--move);color:#241a00;border-color:var(--move)}
.item[data-v="off"]{background:#f8514912}.item[data-v="off"] button[data-a="off"]{background:var(--bad);color:#2b0000;border-color:var(--bad)}
.item[data-v="vague"]{background:#8b949e12}.item[data-v="vague"] button[data-a="vague"]{background:var(--vague);color:#111;border-color:var(--vague)}
select{font:inherit;font-size:12px;background:#0b0d11;color:var(--fg);border:1px solid var(--line);
       border-radius:5px;padding:2px 5px;margin-top:5px}
.hint{color:var(--dim);font-size:12px;padding:0 20px 30px;max-width:1000px}
kbd{background:#21262d;border:1px solid var(--line);border-radius:4px;padding:0 5px;font-size:11px}
"""

JS = r"""
const PH = __PHASES__, DATA = __DATA__;
const KEY = 'flowReview.v1';
let store = JSON.parse(localStorage.getItem(KEY) || '{}');
let cur = 0;

const id = (r, ph, i) => `${r.no}|${ph}|${i}`;
const total = DATA.rows.reduce((a, r) => a + PH.reduce((b, [k]) => b + r.items[k].length, 0), 0);
const doneOf = (r) => PH.reduce((n, [k]) => n + r.items[k].filter((_, i) => store[id(r, k, i)]).length, 0);
const cntOf = (r) => PH.reduce((n, [k]) => n + r.items[k].length, 0);

function save() { localStorage.setItem(KEY, JSON.stringify(store)); paintProgress(); paintList(); }

function paintProgress() {
  const d = Object.keys(store).length;
  document.querySelector('.bar>i').style.width = (100 * d / total) + '%';
  document.getElementById('pg').textContent = `${d} / ${total}`;
}

function paintList() {
  document.querySelectorAll('aside div').forEach((el, i) => {
    const r = DATA.rows[i], d = doneOf(r), c = cntOf(r);
    el.classList.toggle('on', i === cur);
    const n = el.querySelector('.n');
    n.textContent = `${d}/${c}`;
    n.classList.toggle('done', d === c);
  });
}

function esc(s) { return String(s).replace(/[&<>"]/g, m => ({ '&': '&amp;', '<': '&lt;', '>': '&gt;', '"': '&quot;' }[m])); }

function render() {
  const r = DATA.rows[cur], ins = r.inspection;
  const m = document.querySelector('main');
  const c = r.coord, cs = ['편', '장', '절', '관'].map((l, i) => c[i] ? l + c[i] : '').filter(Boolean).join('·');
  let h = `<h2>${esc(r.subject)}</h2><div class="meta">${esc(r.path || '')}<br>
    좌표 <b>${cs}</b>
    ${r.apx3 && r.apx3.length ? ' &nbsp;·&nbsp; 별표 3 제' + r.apx3.join('·') + '호' : ''}
    &nbsp;·&nbsp; 가이드 <b>${esc(r.guide || '없음')}</b>
    &nbsp;·&nbsp; 정기 근거 <b>${esc(ins.periodic_source)}</b>
    ${ins.machines.length ? ' — 안전검사 대상 <b>' + esc(ins.machines.join('·')) + '</b>' : ''}</div>`;

  for (const [k, label] of PH) {
    const its = r.items[k];
    h += `<section class="${its.length ? '' : 'empty'}"><h3>${label}<span class="c">${its.length}건</span></h3>`;
    if (!its.length) {
      h += `<div class="none">${k === 'PERIODIC' && !ins.is_target
        ? '안전검사 대상이 아니고 가이드에도 정기 절차가 없다 — 데이터 결손이 아니다'
        : '비어 있음'}</div>`;
    }
    let grp = null;
    its.forEach((x, i) => {
      // 정기 칸만 근거 강도로 나눈다. 법정(안 하면 위법)과 권고를 섞으면 안내가 혼선이 된다.
      // ★ 판정 기준은 **'권고'가 붙었는가**다. 예전엔 '법정'이 붙었는가로 봤는데, 조문이 정기 칸에
      //   들어오기 시작하자(원문 판독으로 19개 조문) '조문(전용)'이 권고로 떨어졌다.
      //   규칙이 직접 정한 정기 의무를 KOSHA 권고로 표시하는 것은 반대 방향의 오안내다.
      const tier = (s) => (s.indexOf('권고') >= 0 ? 'rec' : 'law');
      if (k === 'PERIODIC') {
        const g = tier(x.source);
        if (g !== grp) { grp = g; h += `<div class="grp ${g}">${g === 'law' ? '법정 — 규칙 조문 · 산업안전보건법 제93조 안전검사' : '권고 — KOSHA 가이드 절차'}</div>`; }
      }
      const key = id(r, k, i), v = store[key];
      const cls = ' ' + tier(x.source);
      h += `<div class="item" data-k="${key}"${v ? ` data-v="${esc(v.v)}"` : ''}>
        <div class="t"><p>${esc(x.text)}</p>
          ${x.evidence ? `<div class="ev">“${esc(x.evidence)}”</div>` : ''}
          <div class="src"><span class="tag${cls}">${esc(x.source)}</span>${esc(x.ref)}</div>
          <select data-mv="${key}" style="display:${v && v.v === 'move' ? '' : 'none'}">
            <option value="">→ 맞는 칸 선택</option>
            ${PH.filter(([p]) => p !== k).map(([p, l]) => `<option value="${p}"${v && v.to === p ? ' selected' : ''}>${l}</option>`).join('')}
          </select>
        </div>
        <div class="acts">
          <button data-a="ok"    title="이 칸이 맞다 (1)">✓</button>
          <button data-a="move"  title="다른 칸이다 (2)">↔</button>
          <button data-a="off"   title="이 기인물과 무관하다 (3)">✗</button>
          <button data-a="vague" title="모호하다 (4)">?</button>
        </div></div>`;
    });
    h += `</section>`;
  }
  h += `<div class="hint"><kbd>↑</kbd><kbd>↓</kbd> 항목 이동 · <kbd>1</kbd>맞음 <kbd>2</kbd>다른 칸
        <kbd>3</kbd>무관 <kbd>4</kbd>모호 · <kbd>[</kbd><kbd>]</kbd> 작업종류 이동</div>`;
  m.innerHTML = h;
  window.scrollTo(0, 0);
  paintList();
}

document.addEventListener('click', e => {
  const b = e.target.closest('.acts button');
  if (b) {
    const it = b.closest('.item'), key = it.dataset.k, a = b.dataset.a;
    if (store[key] && store[key].v === a) delete store[key];
    else store[key] = { v: a, to: (store[key] || {}).to || '' };
    it.dataset.v = store[key] ? store[key].v : '';
    if (!store[key]) it.removeAttribute('data-v');
    it.querySelector('select').style.display = store[key] && store[key].v === 'move' ? '' : 'none';
    save(); return;
  }
  const li = e.target.closest('aside div');
  if (li) { cur = +li.dataset.i; render(); }
});

document.addEventListener('change', e => {
  if (e.target.dataset.mv) { const k = e.target.dataset.mv; store[k] = store[k] || { v: 'move' }; store[k].to = e.target.value; save(); }
});

let focus = 0;
document.addEventListener('keydown', e => {
  if (e.target.tagName === 'SELECT') return;
  const items = [...document.querySelectorAll('.item')];
  if (e.key === '[') { cur = (cur - 1 + DATA.rows.length) % DATA.rows.length; focus = 0; render(); return; }
  if (e.key === ']') { cur = (cur + 1) % DATA.rows.length; focus = 0; render(); return; }
  if (e.key === 'ArrowDown') { focus = Math.min(focus + 1, items.length - 1); }
  else if (e.key === 'ArrowUp') { focus = Math.max(focus - 1, 0); }
  else if ('1234'.includes(e.key) && items[focus]) {
    items[focus].querySelectorAll('.acts button')[+e.key - 1].click();
    focus = Math.min(focus + 1, items.length - 1);
  } else return;
  e.preventDefault();
  items.forEach(x => x.style.outline = '');
  if (items[focus]) { items[focus].style.outline = '2px solid #1f6feb'; items[focus].scrollIntoView({ block: 'center' }); }
});

document.getElementById('csv').onclick = () => {
  const q = s => `"${String(s == null ? '' : s).replace(/"/g, '""')}"`;
  const L = ['no,subject,phase,source,ref,text,verdict,correct_phase'];
  for (const r of DATA.rows) for (const [k] of PH) r.items[k].forEach((x, i) => {
    const v = store[id(r, k, i)];
    if (!v) return;
    L.push([r.no, r.subject, k, x.source, x.ref, x.text, v.v, v.to || ''].map(q).join(','));
  });
  const a = document.createElement('a');
  a.href = URL.createObjectURL(new Blob(['﻿' + L.join('\n')], { type: 'text/csv' }));
  a.download = 'flow_review.csv'; a.click();
};

document.getElementById('rst').onclick = () => {
  if (confirm('판정을 전부 지운다. 되돌릴 수 없다.')) { store = {}; save(); render(); }
};

// 113종 전부를 순서대로 넘기기엔 많다. 재료가 두꺼운 그룹(별표·안전검사가 붙은 곳)을
// 먼저 보도록 ★를 달아 둔다. 순서 자체는 좌표순을 유지한다 — 임의 정렬은 위치 감각을 뺏는다.
document.querySelector('aside').innerHTML = DATA.rows.map((r, i) => {
  const rich = (r.apx3 && r.apx3.length) || r.inspection.is_target || r.guide;
  return `<div data-i="${i}"><span>${rich ? '★ ' : ''}${esc(r.subject.slice(0, 22))}</span><span class="n"></span></div>`;
}).join('');
render(); paintProgress();
"""

HTML = """<!doctype html><html lang="ko"><meta charset="utf-8">
<title>흐름 라벨 검수 — 기인물 그룹별</title><style>__CSS__</style>
<header>
  <h1>흐름 라벨 검수</h1>
  <span class="bar"><i></i></span><span id="pg" style="font-variant-numeric:tabular-nums"></span>
  <button id="csv">CSV 내보내기</button><button id="rst">초기화</button>
</header>
<div class="wrap"><aside></aside><main></main></div>
<script>__JS__</script></html>"""


def main() -> None:
    data = json.loads(SRC.read_text(encoding="utf-8"))
    n = sum(len(v) for r in data["rows"] for v in r["items"].values())
    js = (JS.replace("__PHASES__", json.dumps(PHASES, ensure_ascii=False))
            .replace("__DATA__", json.dumps(data, ensure_ascii=False).replace("</", "<\\/")))
    OUT.write_text(HTML.replace("__CSS__", CSS).replace("__JS__", js), encoding="utf-8")
    print(f"작업종류 {len(data['rows'])}종 · 검수 항목 {n}개")
    print(f"→ {OUT}")


if __name__ == "__main__":
    main()
