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
    group_by_date,
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


def run() -> None:
    print(f"[전처리 시작] CSV의 전체 대화를 파싱합니다.")

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
        date_groups = group_by_date(rows)

        if not date_groups:
            print("  대화 내용이 없습니다. 건너뜀.")
            continue

        sorted_dates = sorted(date_groups.keys())
        latest_date = sorted_dates[-1]

        for target_date in sorted_dates:
            target_rows = date_groups[target_date]
            
            dir_name = f"{target_date.strftime('%Y-%m-%d')}_{room_name}"
            out_dir = config.OUTPUT_DIR / dir_name
            
            if out_dir.exists():
                print(f"  {target_date} 날짜는 이미 파싱됨. 건너뜀.")
                continue

            print(f"  새로운 대화 파싱 중: {target_date} ({len(target_rows)}건)")
            out_dir.mkdir(parents=True, exist_ok=True)

            save_chat_log(format_as_txt(target_rows), out_dir, target_date)
            print(f"  대화록 저장 완료: {out_dir.name}")

            links = extract_links(target_rows)
            if links:
                print(f"  발견된 링크 {len(links)}개 크롤링 중...")
                links_info = [scrape_link_metadata(url) for url in links]
                links_text = format_links(links_info)
                (out_dir / f"링크목록_{target_date.strftime('%Y%m%d')}.txt").write_text(links_text, encoding="utf-8")
                print("  링크 목록 저장 완료")

            file_refs = extract_file_refs(target_rows)
            moved_docs = move_explicit_files(file_refs, out_dir)
            if moved_docs > 0:
                print(f"  문서 파일 이동 완료: {moved_docs}개")

        media_to_move = file_clusters.get(csv_path, [])
        if media_to_move:
            latest_out_dir = config.OUTPUT_DIR / f"{latest_date.strftime('%Y-%m-%d')}_{room_name}"
            latest_out_dir.mkdir(parents=True, exist_ok=True)
            moved_media = move_clustered_media(media_to_move, latest_out_dir)
            if moved_media > 0:
                print(f"  미디어 파일 일괄 이동 완료 ({latest_date} 폴더): {moved_media}개")

        csv_path.unlink()
        print("  원본 CSV 삭제 완료")

    print("\n[전처리 완료]")


if __name__ == "__main__":
    run()
