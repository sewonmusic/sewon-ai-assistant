# 이카운트 전일판매현황 자동 수집 파이프라인 구현 완료 보고서

**작업일:** 2026-06-23  
**참조 PRD:** `PRD_ecount_sales.md`

## 구현 파일
- `src/ecount_mapping/sync_sales.py` — 메인 파이프라인 (신규 생성)
- `src/ecount_mapping/db.py` — `init_sales_table`, `upsert_sales`, `lookup_sku` 함수 추가
- `requirements.txt` — `playwright>=1.40.0` 추가
- `logs/` 디렉토리 생성 (cron 로그 저장용)

## 구현 과정에서 발견한 이슈 및 해결

### 1. Gmail IMAP 한글 검색 불가
- **이슈:** `imaplib.search()`에 한글 SUBJECT 조건(`"판매현황"`)을 직접 전달하면 ASCII 인코딩 오류 발생.
- **해결:** IMAP에서 발신자(`ecountnotice@ecount.com`)로만 1차 필터링 후, Python에서 제목 2차 필터링.

### 2. 이카운트 링크의 다단계 JS 리다이렉트
- **이슈:** 메일 링크(`l.ecount.com/...`) 접속 시 S3 랜딩 페이지 → `login.ecount.com` → `loginab.ecount.com` V5 SPA로 3단계 리다이렉트 발생. `page.goto()` 직후 DOM은 아직 로그인 폼 상태.
- **해결:** `page.wait_for_load_state("networkidle")`로 리다이렉트 완료 대기.

### 3. 새로운 기기 로그인 알림 모달
- **이슈:** Playwright(헤드리스 브라우저)는 매번 새 기기로 인식되어 로그인 후 "새로운 기기 로그인 알림" 모달이 팝업되어 이후 렌더링 차단.
- **해결:** `page.wait_for_selector("button:has-text('등록안함')")` → 클릭으로 모달 자동 해제.

### 4. 판매현황 테이블 렌더링 타이밍
- **이슈:** `networkidle` 완료 후에도 React SPA가 테이블을 마운트하기 전에 `_parse_table`이 호출되어 테이블 미발견 오류.
- **해결:** `page.wait_for_selector("th:has-text('품목명')")`로 실제 데이터 헤더가 렌더링될 때까지 대기.

### 5. `일자-No.` 합쳐진 컬럼 구조
- **이슈:** PRD에는 `일자`와 `No.`가 별도 컬럼으로 가정되어 있으나, 실제 페이지는 `"2026/06/22 -1"` 형태의 단일 컬럼.
- **해결:** 정규식 `r"^(\S+)\s*-\s*(\d+)$"`으로 분리.

### 6. 소계·합계 행 혼입
- **이슈:** 스크래핑 결과에 "합계", "2026/06 계" 같은 소계 행이 포함됨.
- **해결:** `sale_date`가 `YYYY/MM/DD` 패턴이 아닌 행을 파싱 단계에서 제외.

### 7. 품목명에 `[규격명]` 포함으로 SKU 미매핑
- **이슈:** 이카운트 표의 품목명이 `"던롭 피크 TORTEX TRIANGLE, 0.50MM [0.5]"` 형태로 `[규격명]`이 붙어 있어 `product_master` 조회 실패.
- **해결:** 매핑 조회 시 `re.sub(r"\s*\[.*?\]\s*$", "", name)`으로 말미 `[...]` 제거. DB 저장은 원본 유지.

## 최종 실행 결과
- 53건 적재 (소계 행 2개 자동 제외), SKU 매핑 53/53 전건 성공
- cron 등록: 매일 오전 9시 자동 실행 (`/usr/sbin/cron` Full Disk Access 권한 부여 완료)

---

# PRD 버전 1.4 롤백 작업 완료 보고서

`PRD_kakao.md`의 버전 1.4(구글 클라우드 인증 추가) 내용 삭제 요청에 따라 관련 문서 롤백을 완료했습니다.

## 변경 사항 및 결과

### 1. 문서 수정 및 복구
- **[PRD_kakao.md](file:///Users/sewon/Projects/aim/PRD_kakao.md)**:
  - 수정 이력에서 `2026-06-23 (v1.4)` 항목을 제거했습니다.
  - 본문에서 구글 서비스 API 호출을 위한 Google Cloud CLI 인증 안내 경고 블록을 삭제했습니다.
- **[PRD.md](file:///Users/sewon/Projects/aim/PRD.md)**:
  - 수정 이력에서 `2026-06-23 (v2.2)` 항목을 제거했습니다.
  - 본문의 소프트웨어 스택 및 클라우드 연동 권한 명세 항목에서 gcloud 관련 내용을 삭제했습니다.

### 2. 코드 영향도 및 복구 검증
- 프로젝트 소스 코드를 대상으로 `gcloud` 및 `google` 연동 코드가 포함되어 있는지 전체 검색(Grep)을 수행했습니다.
- 분석 결과, Google Cloud CLI 인증 관련 내용은 PRD 기획 문서 상의 명세에만 추가되었을 뿐, 실제 실행 코드(`src` 디렉토리 내 파이썬 모듈 등) 상에는 추가되거나 변경된 코드가 없었음을 확인했습니다.
- 따라서 코드 단에서의 롤백은 불필요하였으며, 문서 롤백 완료 후 `git status` 상에서 워킹 트리가 완벽히 깨끗한(clean) 상태로 복구되었습니다.
