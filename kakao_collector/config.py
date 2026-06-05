from pathlib import Path

# 프로젝트 루트 기준 경로
_BASE = Path(__file__).parent.parent

RAW_DIR = _BASE / "[00_수동다운로드_RAW]"
OUTPUT_DIR = _BASE / "[01_정리전_대화및파일]"
JOURNAL_DIR = _BASE / "[02_정리완료_업무일지]"
ARCHIVE_DIR = _BASE / "[03_아카이브]"
KAKAO_FOLDER_NAME = "거래처"

# 필요한 폴더를 미리 생성
RAW_DIR.mkdir(parents=True, exist_ok=True)
OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
JOURNAL_DIR.mkdir(parents=True, exist_ok=True)
ARCHIVE_DIR.mkdir(parents=True, exist_ok=True)

# 이전 GUI용 ROOM_LIST_FALLBACK은 삭제함.
