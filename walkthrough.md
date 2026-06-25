# 가격 정보 NULL → 0 처리 수정

**작업일:** 2026-06-23

## 배경
- `product_master`의 `purchase_price`, `sale_price` 중 153건/157건이 NULL로 저장되어 있었음
- `ecount_sales_history`의 가격 컬럼(`unit_price` 등) 8건도 NULL
- NULL이 섞이면 이익 계산(`sale_price - purchase_price`) 결과도 NULL이 되어 집계 오류 발생

## 처리 내용

### 1. 기존 DB 데이터 업데이트
- `product_master`: NULL `purchase_price` 153건, `sale_price` 157건 → 0으로 일괄 업데이트
- `ecount_sales_history`: NULL 가격 컬럼 8건 → 0으로 일괄 업데이트

### 2. 코드 수정 (앞으로의 입력도 0으로)
- `src/ecount_mapping/api_client.py` — `_float()`: `None`, `""`, `"0.0000000000"` 반환값을 `None` → `0.0`으로 변경
- `src/ecount_mapping/sync_sales.py` — `to_num()`: 빈 문자열일 때 `None` → `cast(0)`으로 변경

---

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

# 카카오톡 전처리 버그 수정 및 엑셀 내용 업무일지 임베딩 기능 추가

**작업일:** 2026-06-25

## 배경 및 이슈

### 1. 엑셀 파일이 잘못된 거래처 폴더로 배분되는 버그
- `cluster_unclassified_files()` 함수가 미디어 파일뿐 아니라 엑셀 파일도 타임스탬프 기준으로 클러스터링하고 있었음
- 엑셀 파일명에는 카카오톡 형식의 타임스탬프가 없어 파일시스템 수정 시각(mtime)을 사용하게 됨
- 여러 거래처 CSV를 동시에 내보내면 mtime이 유사하여 엑셀이 의도하지 않은 거래처 폴더로 이동하는 오류 발생

### 2. 업무일지 MD에서 엑셀 내용 확인 불가
- 생성된 업무일지 MD 파일에 엑셀 파일명만 기록되어 옵시디언에서 실제 내용을 확인할 수 없었음

## 처리 내용

### 1. 엑셀 파일 타임스탬프 클러스터링 제외 (`src/kakao_collector/file_manager.py`)
- `cluster_unclassified_files()`의 대상 확장자를 미디어 파일(`.jpg`, `.jpeg`, `.png`, `.webp`, `.mp4`, `.mov`, `.gif`)로만 제한
- 엑셀/문서 파일은 대화 내 "파일: 파일명" 형태로 명시된 경우(`move_explicit_files()`)에만 해당 거래처 폴더로 이동

### 2. 업무일지 MD에 엑셀 Markdown 표 임베딩 (`src/kakao_collector/journal_generator.py`)
- `_excel_to_markdown()` 헬퍼 함수 추가: pandas + openpyxl로 엑셀 시트를 읽어 Markdown 표로 변환 (시트당 최대 100행)
- 멀티 시트 지원: 각 시트를 `### 시트명` 헤더 아래 별도 표로 출력
- 업무일지 MD 파일에 `## 📊 첨부 문서` 섹션으로 표 내용 추가

### 3. LLM 프롬프트에는 파일명만 전달 (`src/kakao_collector/llm_processor.py`)
- 엑셀 표 내용을 이미지 여러 장과 함께 LLM에 전달하면 Anthropic API 413(Request Too Large) 오류 발생
- LLM에는 파일명만 전달하고, MD 파일 하단에 표를 직접 append하는 방식으로 해결
- `generate_journal_markdown()` 시그니처에 `excel_contents` 파라미터 추가 (수신만, 프롬프트 미포함)

### 4. `requirements.txt`에 `openpyxl` 추가
- pandas의 `.xlsx` 읽기 엔진으로 openpyxl 필요

## 최종 결과
- `2026-06-24_기타네트:박철우` 아카이브 폴더로 테스트 완료
- `## 📊 첨부 문서` 섹션에 `260624_모노_.xlsx`(MONO 케이스 가격표) 전체 내용이 Markdown 표로 포함됨
- LLM 요약에서도 파일명 기반으로 첨부파일 내용 정상 언급

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

---

# 옵시디언 태그 오류 수정 및 거래처 폴더 분리 작업 완료 보고서

**작업일:** 2026-06-24

## 배경 및 이슈
- **폴더 관리 문제:** `02_journals` 디렉토리에 모든 거래처의 업무일지가 섞여 있어 관리가 어려웠음.
- **태그 인식 오류:** LLM이 생성한 태그에 띄어쓰기(`Gold Series`)나 특수문자(`콜텍:김형근`)가 포함되어 옵시디언에서 정상적으로 태그를 렌더링하고 검색하지 못하는 문제가 발생.

## 처리 내용

### 1. 거래처별 폴더 자동 분리
- **코드 수정:** `src/kakao_collector/journal_generator.py`를 수정하여, 업무일지 생성 시 파일명에 있는 담당자명을 제외한 '순수 거래처명'으로 하위 폴더를 자동 생성하고 그 안에 저장하도록 변경.
- **마이그레이션:** 기존 `02_journals` 하위에 있던 65개의 마크다운 파일들을 분석하여 `콜텍/`, `데임사이어/`, `기타네트/` 등의 거래처별 폴더로 모두 일괄 이동 완료. (단, 파일명에는 담당자명 유지)

### 2. 옵시디언 태그 포맷팅 교정
- **프롬프트 개선:** `src/kakao_collector/llm_processor.py`의 `SYSTEM_PROMPT`를 수정하여 다음 규칙을 적용함.
  - 거래처명과 담당자명을 각각 독립적인 태그로 분리 (예: `[콜텍, 김형근]`)
  - 상품명 등 띄어쓰기가 포함된 경우 언더바(`_`)로 치환 (예: `Gold_Series`)
  - 콜론, 마침표 등 옵시디언 태그 오류를 유발하는 특수문자 제거
- **마이그레이션:** `fix_tags.py` 스크립트를 작성하여 60개의 기존 파일들의 YAML Frontmatter(`tags: [...]`)를 순회하며 위 규칙에 맞게 일괄 변환 및 덮어쓰기 완료.
