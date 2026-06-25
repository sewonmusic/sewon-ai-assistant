# 📋 [Sub-PRD 1.5] Ecount 통합 매핑 DB 및 채널 정규화

## 0. 문서 수정 이력 (Revision History)
* **2026-06-25 (v1.3):**
  * Phase 1.5-B 데이터 수집 단계에 네이버/쿠팡 무료 공식 API를 통한 상품 목록 자동 수집 흐름 명시
  * Phase 1.6 (채널 상태 관제탑) 신규 추가: 채널별 판매 상태 의도적 불일치 관리, 네이버/쿠팡 무료 API 연동
  * DB 스키마에 `channel_status_control` 테이블 추가
* **2026-06-17 (v1.2):** Phase 1.5-A(이카운트 마스터 DB)와 Phase 1.5-B(채널 정규화)로 단계 분리 및 난이도 명시
* **2026-06-17 (v1.1):** 검토 의견 반영 (DB 제약사항, 예외 처리, 메트릭, 비범위 등 추가)
* **2026-06-17 (v1.0):** 최초 작성

---

## 1. 프로젝트 개요
* **상위 프로젝트:** 세원뮤직 통합 업무 자동화 프로젝트 (Project: aim)
* **하위 프로젝트 목표:** 이카운트 ERP 연동 및 SQLite 기반 통합 매핑 DB를 구축하여, 다채널 쇼핑몰(스마트스토어, 쿠팡 등)과 거래처 간의 상품명/상품코드(SKU) 불일치 문제를 해결하고 데이터를 정규화합니다.
* **추진 전략 (복잡도 격리):** Ecount API 통신 및 마스터 DB 구축(Phase 1.5-A)과, 비정형 쇼핑몰 데이터의 AI 매핑(Phase 1.5-B)은 완전히 다른 성격의 과제이므로, 복잡도를 분리하여 순차적으로 개발합니다.
* **대상 범위:** 이카운트 ERP 마스터 데이터, 다채널 쇼핑몰 상품 코드, 자동 매핑 AI 추론 파이프라인
* **비범위 (Out of Scope):** 
  * 1:N / N:1 묶음/세트 상품의 매핑 처리 (단일 상품 매핑에 우선 집중)
  * 채널별 판매 가격 동기화 로직 (매핑 자체에 집중)
* **선행 의존성:** 카카오톡 대화록 기반 상품 데이터 전처리 파이프라인 (Phase 1)
* **성공 지표:** 
  * AI 자동 매핑 최초 추론 정확도 85% 이상 달성
  * 휴먼 인 더 루프 검토 소요 시간 주당 2시간 이내 단축
* **최종 저장소:** 로컬 SQLite 데이터베이스 (`database/sewon_mapping.db`) 및 옵시디언 검토 파일 (`obsidian_vault/Mapping_Review_Pending.md`)

---

## 2. 단계별 실행 로드맵 및 상세 워크플로우

### 🟡 Phase 1.5-A: 이카운트 마스터 DB 독립 구축 (현재 포커스)
**개발 포커스:** API 통신 안정성 및 단일 진실 공급원(Single Source of Truth) 확보. 채널 매핑은 고려하지 않습니다.
1. **로컬 데이터베이스 초기화:** `database/sewon_mapping.db` 생성 및 `product_master` 테이블 스키마 확립.
2. **이카운트 인증 모듈 개발:** Ecount API 특유의 Zone 라우팅 및 Session ID 발급/유지 로직 구현.
3. **마스터 데이터 동기화:** 
   * 이카운트 품목 리스트를 Fetch하여 `product_master` 테이블을 업데이트(UPSERT)합니다. 
   * **예외 처리:** API 호출 실패 시 최대 3회 재시도. 최종 실패 시 마지막 스냅샷 유지 및 관리자 알림 발송.
   * **단종 처리:** 단종된 품목은 물리 삭제가 아닌 `is_active=False`로 Soft Delete 처리합니다.

### 🔴 Phase 1.5-B: AI 기반 다채널 정규화 및 매핑 (추후 진행)
**개발 포커스:** 쇼핑몰별 상이한 규격(데이터 파편화) 해결, AI 추론 및 Human-in-the-loop 검증.
1. **데이터 수집 및 정제:** 네이버 커머스 API(`GET /v2/products`) 및 쿠팡 Wing open API를 통해 등록된 전체 상품 목록(상품 ID, 옵션 ID 포함)을 자동 수집합니다. 수집 결과를 `channel_mapping` 테이블의 `channel_product_code` / `channel_option_code` 컬럼에 반영합니다.
2. **AI 자동 매핑:** LLM을 활용해 수집된 채널 상품명을 이카운트 SKU와 비교하여 추론합니다.
   * 결과는 `channel_mapping` 테이블에 `PENDING` 상태로 UPSERT 됩니다.
   * `UNIQUE(channel_name, channel_option_code)` 제약을 통해 중복 생성을 방지합니다.
   * `REJECTED` 이력이 있는 건은 프롬프트 컨텍스트에 주입하거나 추론에서 제외하여 무한 반복을 방지합니다.
3. **관리자 검증 및 역동기화:** 
   * `PENDING` 상태의 매핑 정보는 `Mapping_Review_Pending.md` 파일로 추출됩니다. (신뢰도 순 정렬, 파싱을 위한 숨김 식별자 삽입)
   * 파일 내보내기 시 스냅샷 타임스탬프를 기록하여 Race Condition을 감지합니다.
   * 관리자 체크 완료 후 역동기화 스크립트 실행 시, 파싱 실패 행은 Skip 후 로그에 기록하며 성공한 행만 DB에 최종 반영(`APPROVED` 또는 `REJECTED`)하고 감사 로그(`reviewed_at`, `reviewed_by`)를 갱신합니다.

### ⏳ Phase 1.6: 채널 상태 관제탑 (Phase 1.5-B 완료 후 착수)
**개발 포커스:** 채널별 판매 상태의 의도적 불일치를 기록하고 API로 즉시 제어하는 "상태 관제탑" 구축.

**배경:** 이카운트 재고가 0이더라도 스마트스토어는 위탁 발송으로 판매중 유지, 쿠팡은 즉시 품절 처리하는 등 채널마다 의도적으로 다른 상태를 운영해야 한다. 이를 머릿속이나 수기로 관리하는 한계를 DB로 해결한다.

**비범위:** 샵링커 유료 API(약 700만원) 연동 — 비용 대비 효용 없음. 네이버/쿠팡 무료 공식 API로 직접 대체.

**핵심 기능:**
1. **상태 조회:** 네이버 커머스 API / 쿠팡 Wing open API를 통해 현재 각 채널의 판매 상태 및 재고 수량을 조회하여 `channel_status_control` 테이블에 동기화합니다.
2. **상태 변경:** API를 통해 특정 채널의 판매 상태(판매중/품절/판매중지) 및 재고 수량을 직접 수정합니다.
3. **불일치 기록:** `memo` 컬럼에 의도적 불일치 사유(예: "위탁 발송 가능하여 스마트스토어 판매중 유지")를 기록하여 다음 작업 시 맥락을 보존합니다.
4. **챗봇 연동 (Phase 2):** "네이버 품절 처리해줘" 같은 자연어 명령을 받아 백엔드 API를 호출하는 인터페이스로 확장됩니다.

---

## 3. 데이터베이스 스키마 설계 (`sewon_mapping.db`)

### 3.1. `product_master` (기준 정보 테이블)
* `id`: PK (Primary Key)
* `ecount_sku`: 이카운트 품목코드 (절대기준값, Unique)
* `product_name`: 상품명
* `purchase_price`: 매입가(원가)
* `sale_price`: 기본 판매가
* `is_active`: 사용 여부 / 단종 처리 플래그 (Boolean, Default: True)
* `sync_source`: 동기화 출처 (API / Excel / Crawl)
* `updated_at`: 최종 업데이트 일시

### 3.2. `channel_mapping` (채널 연결 테이블)
* `id`: PK
* `ecount_sku`: FK (`product_master` 참조)
* `channel_name`: 쇼핑몰 또는 연동 솔루션명 (예: 스마트스토어, 쿠팡 등)
* `channel_product_code`: 쇼핑몰 자체 부모 상품코드
* `channel_option_code`: 쇼핑몰 자체 자식/옵션 코드
* **`UNIQUE(channel_name, channel_option_code)`**: 채널 내 옵션 코드 중복 방지 제약
* `status`: 승인 상태 (`PENDING`, `APPROVED`, `REJECTED`)
* `confidence_score`: AI 매핑 추론 신뢰도 (0.0 ~ 1.0)
* `ai_reason`: AI 매핑 추론 근거 설명
* `reject_reason`: 거절 사유 (REJECTED 상태일 경우 재학습 컨텍스트 용도)
* `reviewed_by`: 검토자 식별자
* `reviewed_at`: 최종 검토 일시

### 3.3. `channel_status_control` (채널 상태 관제 테이블)
Phase 1.5-B의 `channel_mapping`에서 확정된 ID를 기반으로, 각 채널의 실시간 판매 상태를 기록하고 제어합니다.
* `id`: PK
* `ecount_sku`: FK (`product_master` 참조)
* `channel_name`: 채널명 (스마트스토어, 쿠팡 등)
* `channel_product_id`: 쇼핑몰 부모 상품 ID
* `channel_option_id`: 쇼핑몰 옵션 ID
* `channel_status`: 현재 판매 상태 (`판매중`, `품절`, `판매중지`)
* `channel_stock_qty`: 현재 채널에 등록된 재고 수량
* `last_synced_at`: 마지막 API 동기화 시각
* `memo`: 의도적 불일치 사유 메모 (예: "위탁 발송 가능, 스마트스토어 판매중 유지")
* **`UNIQUE(channel_name, channel_option_id)`**: 채널 내 옵션 중복 방지 제약

---

## 4. 디렉토리 구조 및 파일 관리
* `src/ecount_mapping/`: 이카운트 API 통신 및 매핑 파이프라인 로직 하위 모듈
* `database/sewon_mapping.db`: 로컬 통합 매핑 DB
* `obsidian_vault/Mapping_Review_Pending.md`: 고정 테이블 포맷 기반 관리자 UI 역할 문서
