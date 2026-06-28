# -*- coding: utf-8 -*-
"""SSOT 탐색기 생성: 16개 흐름도(.md) → self-contained HTML 한 장.

- Mermaid 흐름도 전부 렌더(marked.js + mermaid.js CDN)
- 모듈별 조문 점검표: 실제 제목(article-texts.json) + [A]/[B](article_signatures.jsonl) + 삭제/존재안함 플래그
- 조문 역인덱스: 조문 → 이 조문을 인용하는 모듈들 (검색 가능)

재생성: python3 docs/knowledge/감독관-판단기준/build_ssot_explorer.py
출력:   docs/knowledge/감독관-판단기준/ssot_explorer.html (브라우저로 열기 — 인터넷 필요: CDN)
"""
import json, re, html
from pathlib import Path

ROOT = Path(__file__).resolve().parents[3]
SSOT = ROOT / "docs/knowledge/감독관-판단기준"
ARTICLES = ROOT / "data-team/02-extraction/pipe-A/data/article-texts.json"
SIGS = ROOT / "data-team/05-enrichment/runtime-artifacts/article_signatures.jsonl"
OUT = SSOT / "ssot_explorer.html"

RULE = json.loads(ARTICLES.read_text(encoding="utf-8"))["laws"]["RULE"]
obs = {}
for ln in SIGS.read_text(encoding="utf-8").splitlines():
    if ln.strip():
        o = json.loads(ln)
        obs[o["article_code"]] = (o.get("observable") or "").strip()

CODE_TOKENS = re.compile(r"제(\d+)조의(\d+)|제(\d+)의(\d+)|제(\d+)조|제(\d+)")


def expand_codes(text):
    codes = set()
    for a, b in re.findall(r"제(\d+)(?:조)?\s*~\s*(\d+)", text):
        if int(b) - int(a) < 60:
            for n in range(int(a), int(b) + 1):
                codes.add(f"제{n}조")
    for m in re.finditer(r"제(\d+)(?:조)?((?:\s*[·ㆍ]\s*\d+)+)", text):
        codes.add(f"제{m.group(1)}조")
        for n in re.findall(r"\d+", m.group(2)):
            codes.add(f"제{n}조")
    for m in CODE_TOKENS.finditer(text):
        if m.group(1) and m.group(2):
            codes.add(f"제{m.group(1)}조의{m.group(2)}")
        elif m.group(3) and m.group(4):
            codes.add(f"제{m.group(3)}조의{m.group(4)}")
        elif m.group(5):
            codes.add(f"제{m.group(5)}조")
        elif m.group(6):
            codes.add(f"제{m.group(6)}조")
    return codes


def code_key(c):
    m = re.match(r"제(\d+)조(?:의(\d+))?", c)
    return (int(m.group(1)), int(m.group(2) or 0)) if m else (99999, 0)


def badge(code):
    if code not in RULE:
        return ("err", "존재안함")
    if RULE[code].get("deleted"):
        return ("del", "삭제")
    o = obs.get(code)
    return {"yes": ("a", "[A]"), "partial": ("ap", "[A·부분]"), "no": ("b", "[B]")}.get(o, ("q", "?"))


def seg(md):
    out, i = [], 0
    for m in re.finditer(r"```mermaid\n(.*?)```", md, re.DOTALL):
        if m.start() > i:
            out.append(("md", md[i:m.start()]))
        out.append(("mermaid", m.group(1).rstrip()))
        i = m.end()
    if i < len(md):
        out.append(("md", md[i:]))
    return out


modules = []
for f in sorted(SSOT.glob("*.md")):
    md = f.read_text(encoding="utf-8")
    title = next((l[2:].strip() for l in md.splitlines() if l.startswith("# ")), f.stem)
    codes = sorted(expand_codes(md), key=code_key)
    modules.append({"file": f.name, "name": f.stem, "title": title, "segs": seg(md),
                    "codes": [(c, RULE.get(c, {}).get("title", "—")) + badge(c) for c in codes]})

rev = {}
for mod in modules:
    for c, *_ in mod["codes"]:
        rev.setdefault(c, set()).add(mod["name"])

# ── summary ──
all_codes = sorted(rev, key=code_key)
n_err = sum(1 for c in all_codes if c not in RULE)
n_del = sum(1 for c in all_codes if c in RULE and RULE[c].get("deleted"))
n_b = sum(1 for c in all_codes if badge(c)[0] == "b")
n_a = sum(1 for c in all_codes if badge(c)[0] in ("a", "ap"))

E = html.escape

# ── module sections ──
mod_html, nav = [], []
for mod in modules:
    nav.append(f'<a href="#{E(mod["name"])}">{E(mod["name"])}</a>')
    body = []
    for typ, content in mod["segs"]:
        if typ == "mermaid":
            body.append(f'<pre class="mermaid">{E(content)}</pre>')
        else:
            if content.strip():
                body.append(f'<div class="md-src">{E(content)}</div>')
    rows = []
    for c, t, cls, lab in mod["codes"]:
        rows.append(f'<tr><td class="c">{E(c)}</td><td>{E(t)}</td>'
                    f'<td><span class="badge {cls}">{E(lab)}</span></td></tr>')
    tbl = ('<table class="codes"><thead><tr><th>조문</th><th>실제 제목(DB)</th><th>가시</th></tr></thead>'
           f'<tbody>{"".join(rows)}</tbody></table>') if rows else "<p class=dim>인용 조문 없음</p>"
    mod_html.append(
        f'<section class="mod" id="{E(mod["name"])}"><h2>{E(mod["title"])} '
        f'<span class="file">{E(mod["file"])}</span></h2>{"".join(body)}'
        f'<details><summary>조문 점검표 · {len(mod["codes"])}건</summary>{tbl}</details></section>')

# ── reverse index ──
rev_rows = []
for c in all_codes:
    t = RULE.get(c, {}).get("title", "—")
    cls, lab = badge(c)
    chips = " ".join(f'<a class="chip" href="#{E(m)}">{E(m)}</a>' for m in sorted(rev[c], key=str))
    rev_rows.append(f'<tr><td class="c">{E(c)}</td><td>{E(t)}</td>'
                    f'<td><span class="badge {cls}">{E(lab)}</span></td>'
                    f'<td>{len(rev[c])}</td><td>{chips}</td></tr>')

TEMPLATE = """<!doctype html><html lang=ko><head><meta charset=utf-8>
<meta name=viewport content="width=device-width,initial-scale=1">
<title>SSOT 탐색기 — 감독관 판단기준</title>
<script src="https://cdn.jsdelivr.net/npm/marked/marked.min.js"></script>
<style>
:root{--bg:#fff;--fg:#1a1d21;--dim:#6b7280;--line:#e5e7eb;--accent:#2563eb;--card:#f9fafb}
*{box-sizing:border-box}body{margin:0;font:14px/1.6 -apple-system,Segoe UI,Roboto,'Malgun Gothic',sans-serif;color:var(--fg);background:var(--bg)}
header{position:sticky;top:0;background:var(--bg);border-bottom:1px solid var(--line);padding:10px 16px;z-index:10}
header h1{margin:0 0 6px;font-size:16px}
.nav{display:flex;flex-wrap:wrap;gap:4px;font-size:12px}
.nav a{padding:2px 7px;border:1px solid var(--line);border-radius:6px;text-decoration:none;color:var(--accent)}
.sum{display:flex;gap:14px;flex-wrap:wrap;font-size:12px;color:var(--dim);margin-top:6px}
.sum b{color:var(--fg)}
.arch{font-size:12.5px;background:#eff6ff;border:1px solid #bfdbfe;border-radius:8px;padding:7px 11px;margin-top:7px;color:#1e3a8a;line-height:1.55}
main{max-width:1100px;margin:0 auto;padding:16px}
.mod{border:1px solid var(--line);border-radius:10px;padding:14px 18px;margin:14px 0;background:var(--bg)}
.mod h2{font-size:16px;margin:.2em 0 .6em;border-bottom:2px solid var(--accent);padding-bottom:4px}
.file{font-size:11px;color:var(--dim);font-weight:400}
.md :is(h1,h2,h3){font-size:14px;margin:.8em 0 .3em}.md h1{display:none}
.md table{border-collapse:collapse;margin:.5em 0;font-size:13px}
.md th,.md td{border:1px solid var(--line);padding:3px 8px;text-align:left}
.md th{background:var(--card)}
.md code{background:var(--card);padding:1px 4px;border-radius:4px;font-size:12px}
.md pre{background:var(--card);padding:8px;border-radius:6px;overflow:auto;font-size:12px}
.mermaid{background:var(--card);border-radius:8px;padding:10px;margin:8px 0;text-align:center}
details{margin-top:8px}summary{cursor:pointer;font-weight:600;font-size:13px;color:var(--accent)}
table.codes{border-collapse:collapse;width:100%;margin-top:8px;font-size:13px}
table.codes th,table.codes td{border:1px solid var(--line);padding:4px 8px;text-align:left}
table.codes th{background:var(--card)}
td.c{font-weight:600;white-space:nowrap}
.badge{font-size:11px;padding:1px 6px;border-radius:10px;font-weight:600;white-space:nowrap}
.badge.a{background:#dcfce7;color:#166534}.badge.ap{background:#fef9c3;color:#854d0e}
.badge.b{background:#e5e7eb;color:#374151}.badge.q{background:#ffedd5;color:#9a3412}
.badge.del{background:#fee2e2;color:#991b1b;text-decoration:line-through}.badge.err{background:#fecaca;color:#7f1d1d}
.chip{display:inline-block;font-size:11px;padding:1px 6px;margin:1px;border:1px solid var(--line);border-radius:6px;text-decoration:none;color:var(--accent)}
#search{width:100%;padding:7px 10px;font-size:14px;border:1px solid var(--line);border-radius:8px;margin:8px 0}
#revtable{border-collapse:collapse;width:100%;font-size:13px}
#revtable th,#revtable td{border:1px solid var(--line);padding:4px 8px;text-align:left;vertical-align:top}
#revtable th{background:var(--card);position:sticky;top:96px}
.dim{color:var(--dim)}
</style></head><body>
<header><h1>SSOT 탐색기 — 감독관 판단기준 <span class=dim style="font-size:11px">(생성물 · build_ssot_explorer.py)</span></h1>
<div class=sum><span>모듈 <b>__NMOD__</b></span><span>인용 조문 <b>__NCODE__</b></span>
<span>가시 [A/A~] <b>__NA__</b></span><span>비가시 [B] <b>__NB__</b></span>
<span>삭제참조 <b class="__DELC__">__NDEL__</b></span><span>존재안함 <b class="__ERRC__">__NERR__</b></span></div>
<div class=sum style="margin-top:3px">배지: <span class="badge a">[A]</span> 가시 · <span class="badge ap">[A·부분]</span> 일부가시 · <span class="badge b">[B]</span> 비가시(절차·측정) · <span class="badge del">삭제</span> · <span class="badge q">?</span> 미상</div>
<div class="arch"><b>모델: 관찰단서 → 조문 (AI 산업안전감독관).</b> 입구 = 사진에서 보이는 <b>① 기인물</b> · <b>② 위험장소·구조</b> · <b>③ 환경조건</b> → <b>E00 관찰단서 카탈로그</b>. 추론: 단서 식별 → 전형 사고(재해형태 H) → 예방 조치(SR/CI) → 조문·Guide·위반조문·행정절차[B].</div>
<div class=nav><a href="#reverse">⟲ 조문 역인덱스</a>__NAV__</div></header>
<main>__MODULES__
<section class="mod" id="reverse"><h2>조문 역인덱스 <span class=file>조문 → 인용 모듈 · 검색</span></h2>
<input id=search placeholder="조문/제목/모듈 검색 (예: 제13조, 안전난간, H01)">
<table id=revtable><thead><tr><th>조문</th><th>실제 제목(DB)</th><th>가시</th><th>#</th><th>인용 모듈</th></tr></thead>
<tbody>__REVROWS__</tbody></table></section></main>
<script type="module">
import mermaid from 'https://cdn.jsdelivr.net/npm/mermaid@11/dist/mermaid.esm.min.mjs';
document.querySelectorAll('.md-src').forEach(el=>{el.innerHTML=marked.parse(el.textContent).replace(/<del>([\\s\\S]*?)<\\/del>/g,'~$1~').replace(/href="([^":/]+?)\\.md"/g,'href="#$1"');el.classList.replace('md-src','md');});
mermaid.initialize({startOnLoad:false,securityLevel:'loose',theme:'default',flowchart:{useMaxWidth:true}});
mermaid.run({querySelector:'.mermaid'}).catch(e=>console.error(e));
const box=document.getElementById('search');
box.addEventListener('input',()=>{const q=box.value.trim().toLowerCase();
document.querySelectorAll('#revtable tbody tr').forEach(tr=>{tr.style.display=tr.textContent.toLowerCase().includes(q)?'':'none';});});
</script></body></html>"""

out = (TEMPLATE
       .replace("__NMOD__", str(len(modules)))
       .replace("__NCODE__", str(len(all_codes)))
       .replace("__NA__", str(n_a)).replace("__NB__", str(n_b))
       .replace("__NDEL__", str(n_del)).replace("__DELC__", "badge del" if n_del else "")
       .replace("__NERR__", str(n_err)).replace("__ERRC__", "badge err" if n_err else "")
       .replace("__NAV__", "".join(nav))
       .replace("__MODULES__", "".join(mod_html))
       .replace("__REVROWS__", "".join(rev_rows)))
OUT.write_text(out, encoding="utf-8")
print(f"OK → {OUT}")
print(f"  modules={len(modules)} codes={len(all_codes)} [A/A~]={n_a} [B]={n_b} 삭제참조={n_del} 존재안함={n_err}")
