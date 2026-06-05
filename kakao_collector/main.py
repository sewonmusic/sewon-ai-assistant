"""
카카오톡 전처리 스크립트 (수동 다운로드 기반)
사용법: python -m kakao_collector.main
"""

import sys
import shutil
from datetime import date
from pathlib import Path

from . import config
from .csv_parser import (
    extract_file_refs,
    extract_links,
    filter_by_date,
    format_as_txt,
    parse_kakao_csv,
)
from .file_manager import (
    create_room_dir,
    get_all_csv_files,
    extract_room_name_from_csv,
    save_chat_log,
    move_explicit_files,
    cluster_unclassified_files,
    move_clustered_media,
)
from .link_scraper import scrape_link_metadata, format_links


def run(target_date: date | None = None) -> None:
    today = target_date or date.today()
    print(f"[전처리 시작] 대상 날짜: {today}")

    csv_files = get_all_csv_files()
    if not csv_files:
        print(f"[종료] '{config.RAW_DIR}' 폴더에 처리할 CSV 파일이 없습니다.")
        return

    print(f"발견된 CSV 파일: {len(csv_files)}개")

    # 모든 CSV 파일에 대해 비정형 파일(사진/동영상 등)을 가장 가까운 시간에 매핑
    file_clusters = cluster_unclassified_files(csv_files)

    for csv_path in csv_files:
        room_name = extract_room_name_from_csv(csv_path.name)
        print(f"\n▶ 처리 중: {room_name} ({csv_path.name})")

        rows = parse_kakao_csv(csv_path)
        today_rows = filter_by_date(rows, today)

        if not today_rows:
            print("  오늘 날짜의 대화가 없습니다. 건너뜀.")
            continue

        print(f"  오늘 메시지: {len(today_rows)}건")

        out_dir = create_room_dir(room_name, today)

        save_chat_log(format_as_txt(today_rows), out_dir, today)
        print(f"  대화록 저장 완료: {out_dir.name}")

        links = extract_links(today_rows)
        if links:
            print(f"  발견된 링크 {len(links)}개 크롤링 중...")
            links_info = [scrape_link_metadata(url) for url in links]
            links_text = format_links(links_info)
            (out_dir / f"링크목록_{today.strftime('%Y%m%d')}.txt").write_text(links_text, encoding="utf-8")
            print("  링크 목록 저장 완료")

        file_refs = extract_file_refs(today_rows)
        moved_docs = move_explicit_files(file_refs, out_dir)
        if moved_docs > 0:
            print(f"  문서 파일 이동 완료: {moved_docs}개")

        media_to_move = file_clusters.get(csv_path, [])
        moved_media = move_clustered_media(media_to_move, out_dir)
        if moved_media > 0:
            print(f"  미디어 파일(시간 근접 매칭) 이동 완료: {moved_media}개")

        shutil.move(str(csv_path), str(out_dir / csv_path.name))
        print("  원본 CSV 이동 완료")

    print("\n[전처리 완료]")


if __name__ == "__main__":
    run()
