from pathlib import Path

# 프로젝트 루트 기준 경로
_BASE = Path(__file__).parent.parent.parent

RAW_DIR = _BASE / "local_data/00_raw"
OUTPUT_DIR = _BASE / "local_data/01_preprocessed"
JOURNAL_DIR = _BASE / "obsidian_vault/02_journals"
ARCHIVE_DIR = _BASE / "local_data/03_archive"
KAKAO_FOLDER_NAME = "거래처"

# 필요한 폴더를 미리 생성
RAW_DIR.mkdir(parents=True, exist_ok=True)
OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
JOURNAL_DIR.mkdir(parents=True, exist_ok=True)
ARCHIVE_DIR.mkdir(parents=True, exist_ok=True)

# 이전 GUI용 ROOM_LIST_FALLBACK은 삭제함.
