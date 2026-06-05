import sys
import shutil
from pathlib import Path
from . import config
from .llm_processor import generate_journal_markdown

def run_journal_generation():
    if not config.OUTPUT_DIR.exists():
        print(f"[종료] 처리할 데이터가 없습니다: {config.OUTPUT_DIR}")
        return

    # [01_정리전_대화및파일] 내의 폴더들 탐색
    folders = [p for p in config.OUTPUT_DIR.iterdir() if p.is_dir()]
    
    if not folders:
        print("[알림] 정리 대기 중인 거래처 폴더가 없습니다.")
        return

    print(f"[업무 일지 생성 시작] 총 {len(folders)}개의 거래처 데이터 발견")

    for folder in folders:
        folder_name = folder.name
        # 폴더명 패턴 분석: YYYY-MM-DD_거래처명
        parts = folder_name.split("_", 1)
        if len(parts) != 2:
            print(f"  [건너뜀] 인식할 수 없는 폴더 포맷: {folder_name}")
            continue
            
        date_str, partner = parts[0], parts[1]
        print(f"\n▶ [{partner}] 업무 일지 작성 중...")
        
        chat_file = folder / f"대화록_{date_str.replace('-', '')}.txt"
        links_file = folder / f"링크목록_{date_str.replace('-', '')}.txt"
        
        if not chat_file.exists():
            print(f"  [경고] 대화록을 찾을 수 없습니다: {chat_file.name}")
            chat_text = "대화록 없음"
        else:
            chat_text = chat_file.read_text(encoding="utf-8")
            
        links_text = links_file.read_text(encoding="utf-8") if links_file.exists() else ""
        
        files_list = []
        doc_dir = folder / "[문서_파일]"
        if doc_dir.exists():
            files_list.extend([f"[문서] {f.name}" for f in doc_dir.iterdir() if f.is_file()])
            
        media_dir = folder / "[사진_동영상]"
        if media_dir.exists():
            files_list.extend([f"[미디어] {f.name}" for f in media_dir.iterdir() if f.is_file()])
            
        # Claude API 호출
        try:
            markdown_content = generate_journal_markdown(
                partner=partner,
                date_str=date_str,
                chat_text=chat_text,
                links_text=links_text,
                files_list=files_list
            )
            
            # 저장
            output_filename = f"{date_str}_{partner.replace(':', '_')}_업무일지.md"
            output_path = config.JOURNAL_DIR / output_filename
            output_path.write_text(markdown_content, encoding="utf-8")
            print(f"  ✅ 업무 일지 생성 완료: {output_filename}")
            
            # 아카이브로 폴더 이동
            archive_path = config.ARCHIVE_DIR / folder_name
            if archive_path.exists():
                shutil.rmtree(archive_path) # 중복 시 덮어쓰기 위해 삭제
            shutil.move(str(folder), str(config.ARCHIVE_DIR))
            print(f"  📦 원본 데이터 아카이브 이동 완료")
            
        except Exception as e:
            print(f"  [오류] API 호출 또는 처리 중 문제 발생: {e}")

if __name__ == "__main__":
    run_journal_generation()
