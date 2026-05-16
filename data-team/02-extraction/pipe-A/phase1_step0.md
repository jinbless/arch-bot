# Phase 1 Step 0: 조문 추출

> 현재 기준 참고 (2026-05-07): 이 문서는 과거 실행 재현 문서다. 최신 product 기준은 루트 `README.md`, `../../docs/ontology/00-integrated-structure.md`, `serving-team/08-app/README.md`, 그리고 이 Pipe의 `status_pipea.md`를 우선 확인한다.

> 최종 업데이트: 2026-04-11
> 스크립트: `scripts/step0_extract_articles.py`

---
## 1. 목적

외부 ignored dependency인 `legalize-kr/`의 법령 JSON 파일에서 5개 법령의 모든 조문을 추출하여 `data/article-texts.json`을 생성한다.

## 2. 설계 원칙

1. **100% 결정론적**: 동일 legalize-kr 커밋 → 동일 출력 (generatedAt 타임스탬프 제외)
2. **LLM 불필요**: 순수 Python 스크립트
3. **사전 스키마 검증**: JSON Schema(`additionalProperties: false`)로 검증 후 저장
4. **null ≠ 생략**: 선택필드가 없으면 `null`. 필드 생략이나 `{}` 금지

## 3. 전제조건

- Python 3.12+
- `pip install jsonschema`
- `legalize-kr` 외부 dependency가 `../../../legalize-kr/` 에 위치 (pipe-A 기준 상대경로, root monorepo에는 import하지 않음)
- legalize-kr에 다음 법령 JSON이 존재:
  - `kr/산업안전보건기준에관한규칙/고용노동부령.json`
  - `kr/산업안전보건법/법률.json`
  - `kr/중대재해처벌등에관한법률/법률.json`
  - `kr/산업안전보건법/시행령.json`
  - `kr/산업안전보건법/시행규칙(고용노동부령).json`

## 4. 파일 구성 (의존성 순서)

### 4.1. `scripts/lib/__init__.py` 
- 빈 파일

### 4.2. `scripts/lib/article_code.py`
- 조문코드 정규화
- 함수: `normalize_article_code(번호)`, `article_code_to_ns_prefix(article_code, law_id)`, `validate_article_code(code)`
### 4.3.`scripts/lib/legalize_reader.py`
- legalize-kr JSON 순회 (→ article_code 의존)
- 함수: `load_law_json(path)`, `extract_articles(law_json, law_id)`
### 4.4.`scripts/lib/schema_validator.py`
- JSON Schema 검증 래퍼
- 함수: `load_schema(schema_path)`, `validate(data, schema)`, `validate_and_write(data, schema_path, output_path)`
### 4.5. `config/law-sources.json`
- 5개 법령 경로
### 4.6. `schemas/article-texts.schema.json`
- 출력 스키마
### 4.7. `scripts/step0_extract_articles.py`
- 메인 (→ legalize_reader, schema_validator 의존)
- 함수: `get_git_commit(repo_path)`, `main()`

## 5. 실행 방법

```bash
cd data-team/02-extraction/pipe-A
python3 scripts/step0_extract_articles.py
```

## 6. 예상 출력

**법령별 조문 수**: RULE 674, OSHA 175, SADA 16, DECREE 119, ENFORCE 243 = 합계 1,227

## 7. 검증 방법

### 결정론성 확인 (2회 실행 시 데이터 해시 동일)

```python
import json, hashlib
with open('data/article-texts.json') as f:
    d = json.load(f)
del d['metadata']['generatedAt']  # 타임스탬프 제외
h = hashlib.md5(json.dumps(d, sort_keys=True, ensure_ascii=False).encode()).hexdigest()
print(f"data-only hash: {h}")
```

## 8. 출력 데이터 구조

```json
{
  "metadata": {
    "generatedAt": "2026-04-11T...",
    "sourceCommit": "d8c121b2...",
    "totalArticles": 1227,
    "deletedArticles": 18,
    "lawSources": {
      "RULE": { "name": "산업안전보건기준에 관한 규칙", "path": "...", "articleCount": 674 },
      "OSHA": { "name": "산업안전보건법", "path": "...", "articleCount": 175 },
      "SADA": { "name": "중대재해 처벌 등에 관한 법률", "path": "...", "articleCount": 16 },
      "DECREE": { "name": "산업안전보건법 시행령", "path": "...", "articleCount": 119 },
      "ENFORCE": { "name": "산업안전보건법 시행규칙", "path": "...", "articleCount": 243 }
    }
  },
  "laws": {
    "RULE": {
      "제24조": {
        "title": "사다리식 통로 등의 구조",
        "fullText": "① 사업주는 사다리식 통로 등을...",
        "deleted": false,
        "section": "편1 총칙 > 장3 통로",
        "annotations": { "개정": ["2019-12-26"], "신설": null },
        "paragraphCount": 2
      }
    }
  }
}
```

END OF FILE.
