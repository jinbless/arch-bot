-- Pilot Multi-SR v2: 격리 테이블 정의
-- 기존 safety_requirements / sr_ns_mapping / sr_article_mapping (v1, 626 SR) 무손상.
-- v2 데이터는 *_v2 테이블에 적재.

CREATE TABLE IF NOT EXISTS safety_requirements_v2 (LIKE safety_requirements INCLUDING ALL);
-- v2 ID는 PILOT prefix로 31자 가능 (예: SR-PILOT_CONSTRUCTION_EQUIP-001) → identifier 컬럼 확장
ALTER TABLE safety_requirements_v2 ALTER COLUMN identifier TYPE VARCHAR(40);

CREATE TABLE IF NOT EXISTS sr_ns_mapping_v2 (
  sr_id   VARCHAR(40) NOT NULL REFERENCES safety_requirements_v2(identifier) ON DELETE CASCADE,
  ns_id   VARCHAR(30) NOT NULL REFERENCES norm_statements(identifier),
  PRIMARY KEY (sr_id, ns_id)
);

CREATE TABLE IF NOT EXISTS sr_article_mapping_v2 (
  sr_id        VARCHAR(40) NOT NULL REFERENCES safety_requirements_v2(identifier) ON DELETE CASCADE,
  law_type     VARCHAR(10) NOT NULL,
  article_code VARCHAR(20) NOT NULL,
  PRIMARY KEY (sr_id, law_type, article_code),
  FOREIGN KEY (law_type, article_code) REFERENCES articles(law_type, article_code)
);

CREATE INDEX IF NOT EXISTS idx_sr_v2_art ON sr_article_mapping_v2(law_type, article_code);
CREATE INDEX IF NOT EXISTS idx_sr_v2_ns  ON sr_ns_mapping_v2(ns_id);
