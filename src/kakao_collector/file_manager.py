import shutil
import re
from datetime import date, datetime
from pathlib import Path

from . import config


def get_all_csv_files() -> list[Path]:
    """RAW_DIR에서 모든 CSV 파일을 찾아서 반환"""
    if not config.RAW_DIR.exists():
        return []
    return list(config.RAW_DIR.glob("*.csv"))


def extract_room_name_from_csv(filename: str) -> str:
    """파일명에서 거래처명 추출. 예: KakaoTalk_Chat_거래처:데임악기_2024... -> 데임악기"""
    m = re.search(r"KakaoTalk_Chat_.*?(?::|_)([^_]+)_\d{4}-\d{2}-\d{2}", filename)
    if m:
        return m.group(1)
    
    m2 = re.search(r"KakaoTalk_Chat_([^:]+)_", filename)
    if m2:
        name = m2.group(1)
        if name.startswith("거래처"):
            name = name.replace("거래처", "").strip(":")
        return name
        
    return filename.replace(".csv", "")


def create_room_dir(room_name: str, target_date: date) -> Path:
    dir_name = f"{target_date.strftime('%Y-%m-%d')}_{room_name}"
    out_dir = config.OUTPUT_DIR / dir_name
    out_dir.mkdir(parents=True, exist_ok=True)
    return out_dir


def save_chat_log(text: str, out_dir: Path, target_date: date) -> None:
    filename = f"대화록_{target_date.strftime('%Y%m%d')}.txt"
    (out_dir / filename).write_text(text, encoding="utf-8")


def cluster_unclassified_files(csv_paths: list[Path]) -> dict[Path, list[Path]]:
    """미디어 파일(사진/동영상)을 가장 가까운 시간의 CSV 파일에 매핑 (5분 이내)"""
    clusters = {csv: [] for csv in csv_paths}

    if not csv_paths:
        return clusters

    media_extensions = {'.jpg', '.jpeg', '.png', '.webp', '.mp4', '.mov', '.gif'}
    csv_times = {csv: csv.stat().st_mtime for csv in csv_paths}

    for file_path in config.RAW_DIR.iterdir():
        if not file_path.is_file():
            continue
        if file_path.suffix.lower() not in media_extensions:
            continue
            
        mtime = file_path.stat().st_mtime
        
        # 파일명에서 시간 추출 시도
        time_match = re.search(r"(\d{4}-\d{2}-\d{2}-\d{2}-\d{2}-\d{2})", file_path.name)
        if time_match:
            try:
                parsed_time = datetime.strptime(time_match.group(1), "%Y-%m-%d-%H-%M-%S")
                mtime = parsed_time.timestamp()
            except ValueError:
                pass
        else:
            time_match2 = re.search(r"(\d{4}-\d{2}-\d{2}-\d{2}-\d{2})", file_path.name)
            if time_match2:
                try:
                    parsed_time = datetime.strptime(time_match2.group(1), "%Y-%m-%d-%H-%M")
                    mtime = parsed_time.timestamp()
                except ValueError:
                    pass

        closest_csv = None
        min_diff = float('inf')
        
        for csv, c_time in csv_times.items():
            diff = abs(c_time - mtime)
            if diff < min_diff:
                min_diff = diff
                closest_csv = csv
                
        # 5분(300초) 이내인 경우에만 매핑
        if closest_csv and min_diff <= 300:
            clusters[closest_csv].append(file_path)
            
    return clusters


def move_clustered_media(media_files: list[Path], out_dir: Path) -> int:
    """클러스터링된 미디어 파일 이동"""
    moved_count = 0
    
    for file_path in media_files:
        if file_path.exists():
            shutil.move(str(file_path), str(out_dir / file_path.name))
            moved_count += 1
            
    return moved_count


def move_explicit_files(file_refs: list[str], out_dir: Path) -> int:
    """명시된 파일명으로 문서/파일 이동"""
    moved_count = 0
    if not file_refs:
        return 0
        
    for fname in file_refs:
        src = config.RAW_DIR / fname
        if src.exists():
            shutil.move(str(src), str(out_dir / fname))
            moved_count += 1
            
    return moved_count
