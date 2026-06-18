import sys
import shutil
import unicodedata
from pathlib import Path
from . import config
from .llm_processor import generate_journal_markdown

def run_journal_generation():
    if not config.OUTPUT_DIR.exists():
        print(f"[종료] 처리할 데이터가 없습니다: {config.OUTPUT_DIR}")
        return

    folders = [p for p in config.OUTPUT_DIR.iterdir() if p.is_dir()]
    if not folders:
        print("[알림] 정리 대기 중인 거래처 폴더가 없습니다.")
        return

    print(f"[업무 일지 생성 시작] 총 {len(folders)}개의 거래처 데이터 발견 (로컬 Vision AI)")

    for folder in folders:
        folder_name = folder.name
        parts = folder_name.split("_", 1)
        if len(parts) != 2:
            continue
            
        date_str = parts[0]
        partner = unicodedata.normalize('NFC', parts[1])
        print(f"\n▶ [{partner}] 업무 일지 작성 중...")
        
        # 대화록 및 링크목록 파일명 정의
        chat_filename = f"대화록_{date_str.replace('-', '')}.txt"
        links_filename = f"링크목록_{date_str.replace('-', '')}.txt"
        
        chat_file = folder / chat_filename
        links_file = folder / links_filename
        
        chat_text = chat_file.read_text(encoding="utf-8") if chat_file.exists() else "대화록 없음"
        links_text = links_file.read_text(encoding="utf-8") if links_file.exists() else ""
        
        doc_list = []
        media_paths = []
        
        # 폴더 루트의 파일을 직접 확인하여 이미지와 문서로 분류
        if folder.exists():
            for f in folder.iterdir():
                if not f.is_file():
                    continue
                if f.name in [chat_filename, links_filename, ".DS_Store"]:
                    continue
                    
                if f.suffix.lower() in ['.jpg', '.jpeg', '.png', '.webp']:
                    media_paths.append(f)
                else:
                    doc_list.append(f.name)
            
        try:
            markdown_content = generate_journal_markdown(
                partner=partner,
                date_str=date_str,
                chat_text=chat_text,
                links_text=links_text,
                doc_list=doc_list,
                media_paths=media_paths
            )
            
            if chat_text and chat_text != "대화록 없음":
                markdown_content += "\n\n## 💬 원본 대화 전문\n```text\n"
                markdown_content += chat_text
                markdown_content += "\n```\n"
            
            output_filename = f"{date_str}_{partner.replace(':', '_')}_업무일지.md"
            output_path = config.JOURNAL_DIR / output_filename
            output_path.write_text(markdown_content, encoding="utf-8")
            print(f"  ✅ 업무 일지 생성 완료: {output_filename}")
            
            archive_path = config.ARCHIVE_DIR / folder_name
            if archive_path.exists():
                shutil.rmtree(archive_path)
            shutil.move(str(folder), str(config.ARCHIVE_DIR))
            print(f"  📦 원본 데이터 아카이브 이동 완료")
            
        except Exception as e:
            print(f"  [오류] AI 모델 호출 중 문제 발생: {e}")
            print(f"  (API 키 및 크레딧 상태, 또는 모델 권한 설정을 확인하세요)")

if __name__ == "__main__":
    run_journal_generation()
