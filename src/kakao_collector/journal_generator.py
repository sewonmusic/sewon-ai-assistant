import sys
import shutil
import unicodedata
from pathlib import Path
from . import config
from .llm_processor import generate_journal_markdown


def _excel_to_markdown(path: Path) -> str:
    import pandas as pd
    engine = "openpyxl" if path.suffix.lower() == ".xlsx" else None
    xl = pd.ExcelFile(path, engine=engine)
    parts = []
    for sheet in xl.sheet_names:
        df = pd.read_excel(xl, sheet_name=sheet, nrows=100).fillna("")
        headers = "| " + " | ".join(str(c) for c in df.columns) + " |"
        sep = "| " + " | ".join(["---"] * len(df.columns)) + " |"
        rows = ["| " + " | ".join(str(v) for v in row) + " |" for _, row in df.iterrows()]
        parts.append(f"### {sheet}\n" + "\n".join([headers, sep] + rows))
    return "\n\n".join(parts)

def run_journal_generation():
    if not config.OUTPUT_DIR.exists():
        print(f"[종료] 처리할 데이터가 없습니다: {config.OUTPUT_DIR}")
        return

    folders = []
    for company_dir in config.OUTPUT_DIR.iterdir():
        if company_dir.is_dir():
            for date_folder in company_dir.iterdir():
                if date_folder.is_dir():
                    folders.append(date_folder)

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
        excel_contents = {}

        # 폴더 루트의 파일을 직접 확인하여 이미지와 문서로 분류
        if folder.exists():
            for f in folder.iterdir():
                if not f.is_file():
                    continue
                if f.name in [chat_filename, links_filename, ".DS_Store"]:
                    continue

                if f.suffix.lower() in ['.jpg', '.jpeg', '.png', '.webp']:
                    media_paths.append(f)
                elif f.suffix.lower() in ['.xlsx', '.xls']:
                    doc_list.append(f.name)
                    try:
                        excel_contents[f.name] = _excel_to_markdown(f)
                    except Exception:
                        pass
                else:
                    doc_list.append(f.name)
            
        try:
            markdown_content = generate_journal_markdown(
                partner=partner,
                date_str=date_str,
                chat_text=chat_text,
                links_text=links_text,
                doc_list=doc_list,
                media_paths=media_paths,
                excel_contents=excel_contents,
            )
            
            if excel_contents:
                markdown_content += "\n\n## 📊 첨부 문서\n"
                for fname, table in excel_contents.items():
                    markdown_content += f"\n### 📄 {fname}\n{table}\n"

            if chat_text and chat_text != "대화록 없음":
                markdown_content += "\n\n## 💬 원본 대화 전문\n```text\n"
                markdown_content += chat_text
                markdown_content += "\n```\n"
            
            output_filename = f"{date_str}_{partner.replace(':', '_')}_업무일지.md"
            
            company_name = partner.split(":")[0]
            partner_dir = config.JOURNAL_DIR / company_name
            partner_dir.mkdir(parents=True, exist_ok=True)
            
            output_path = partner_dir / output_filename
            output_path.write_text(markdown_content, encoding="utf-8")
            print(f"  ✅ 업무 일지 생성 완료: {output_filename}")
            
            archive_company_dir = config.ARCHIVE_DIR / company_name
            archive_company_dir.mkdir(parents=True, exist_ok=True)
            archive_path = archive_company_dir / folder_name
            if archive_path.exists():
                shutil.rmtree(archive_path)
            shutil.move(str(folder), str(archive_company_dir))
            print(f"  📦 원본 데이터 아카이브 이동 완료")
            
        except Exception as e:
            print(f"  [오류] AI 모델 호출 중 문제 발생: {e}")
            print(f"  (API 키 및 크레딧 상태, 또는 모델 권한 설정을 확인하세요)")

if __name__ == "__main__":
    run_journal_generation()
