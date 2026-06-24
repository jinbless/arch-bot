#!/usr/bin/env python
"""이미지 pip freeze 기준 SCA — OSV.dev API 직접 질의 (빌드/설치 불필요, 크로스플랫폼).

pip-audit 가 Windows 에서 uvloop(Linux 전용) 빌드를 시도해 실패하므로, 빌드 없이
OSV.dev querybatch API 로 '이미지에 실제 설치된 정확한 버전'의 알려진 취약점을 조회한다.

사용: python osv_scan.py <freeze.txt> <out.json>
"""
import json
import sys
import urllib.request

freeze_path = sys.argv[1] if len(sys.argv) > 1 else "reports/image-pip-freeze.txt"
out_path = sys.argv[2] if len(sys.argv) > 2 else "reports/osv-image.json"

pkgs = []
for line in open(freeze_path, encoding="utf-8"):
    line = line.strip()
    if not line or line.startswith("#") or "==" not in line:
        continue
    name, ver = line.split("==", 1)
    pkgs.append((name.strip(), ver.strip()))

queries = [{"package": {"name": n.lower(), "ecosystem": "PyPI"}, "version": v} for n, v in pkgs]
req = urllib.request.Request(
    "https://api.osv.dev/v1/querybatch",
    data=json.dumps({"queries": queries}).encode(),
    headers={"Content-Type": "application/json"},
)
results = json.loads(urllib.request.urlopen(req, timeout=60).read())["results"]

findings = []
for (name, ver), res in zip(pkgs, results):
    for v in res.get("vulns", []):
        vid = v["id"]
        # 상세 조회(요약·수정버전)
        try:
            det = json.loads(
                urllib.request.urlopen(f"https://api.osv.dev/v1/vulns/{vid}", timeout=30).read()
            )
        except Exception:
            det = {}
        fixed = []
        for aff in det.get("affected", []):
            for rng in aff.get("ranges", []):
                for ev in rng.get("events", []):
                    if "fixed" in ev:
                        fixed.append(ev["fixed"])
        aliases = det.get("aliases", [])
        cve = next((a for a in aliases if a.startswith("CVE-")), vid)
        findings.append(
            {
                "package": name,
                "version": ver,
                "id": vid,
                "cve": cve,
                "summary": (det.get("summary") or "").strip(),
                "fixed_versions": sorted(set(fixed)),
            }
        )

json.dump(
    {"total_packages": len(pkgs), "vulnerable": len(findings), "findings": findings},
    open(out_path, "w", encoding="utf-8"),
    ensure_ascii=False,
    indent=2,
)
print(f"packages audited: {len(pkgs)}")
print(f"vulnerable findings: {len(findings)}")
for f in findings:
    fv = ", ".join(f["fixed_versions"]) or "(none published)"
    print(f"  - {f['package']}=={f['version']}  {f['cve']}  fix:{fv}  | {f['summary'][:90]}")
