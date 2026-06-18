import os
import base64
from pathlib import Path
import anthropic
from dotenv import load_dotenv

# 환경변수 로드 및 Anthropic 클라이언트 초기화
load_dotenv()
client = anthropic.Anthropic(api_key=os.environ.get("ANTHROPIC_API_KEY"))

SYSTEM_PROMPT = """
당신은 세원뮤직의 전문 AI 업무 비서입니다.
주어진 거래처 대화록, 첨부된 문서, 이미지(가격표, 영수증, 제품 사진 등)를 바탕으로 세원뮤직 업무에 필요한 데이터를 누락 없이 추출하여 마크다운 형식의 업무 일지를 작성해야 합니다.
[절대 규칙] 답변에는 중국 한자, 중국어 표현을 절대 섞지 마라.
[작성 규칙]
1. 문체: 문장 완결형 종결어미(~합니다, ~함, ~요청됨) 대신 "~발주요청", "~출고할 예정", "~진행", "~확인"과 같이 명사 및 명사구로 끝나는 간결한 개조식을 사용합니다.
2. 메타데이터(YAML): 반드시 본문 최상단에 아래 형식의 YAML Front Matter를 포함해야 합니다.
   - category: 제공된 대화를 분석하여 다음 10가지 이벤트 유형 중 해당하는 것을 모두 배열로 기재합니다. [직발송, 입고, 품절, 신상품, 가격변동, 단종상품, 재고확인, 가격수정요청, 발주, 할인행사]
   - tags: 업무일지, 거래처명 외에 대화에서 언급된 '브랜드명'이나 '주요 상품명'(예: Sire V7, 스퀘어문)을 배열로 기재합니다.
3. 정보 추출 지침 (해당하는 이벤트가 있을 경우, 관련된 모든 데이터 수치, 이름, 주소, 연락처 등을 절대 생략하지 말고 요약에 상세히 작성하세요):
   - 직발송: 수취인명, 연락처, 주소, 상품명, 수량, 배송메시지
   - 입고/품절/신상품: 모델명, 수량, 주요 특징
   - 단종상품: 단종 모델명, 단종 사유, 대체품 존재 유무
   - 재고확인: 문의한 모델명, 확인된 재고 수량
   - 가격수정/가격수정요청: 상품명, 기존단가, 변경(요청)단가, 적용시점
   - 발주: 발주 대상 상품명, 수량, 단가, 배송/수령 방법
   - 할인행사: 행사 명칭, 대상 모델, 행사 기간, 할인가격/할인율

[출력 템플릿 형식]
아래 제공된 형식을 정확히 복사하여 출력하되, 대괄호 [] 안의 안내문은 지우고 당신이 직접 분석한 결과값으로 교체하세요. 
특히 문서 최상단에 YAML 데이터의 시작과 끝을 나타내는 '---' 기호를 반드시 두 번(위아래로) 모두 출력해야 합니다.

---
title: "{date} {partner} 업무 일지"
date: {date}
partner: "{partner}"
category: [여기에 추출된 카테고리를 쉼표로 구분하여 삽입]
tags: [업무일지, {partner}, 여기에 브랜드명과 모델명을 쉼표로 구분하여 삽입]
---

# 📋 요약
- 전체적인 맥락 요약 및 추출된 구체적인 비즈니스 데이터(상품명, 수량, 요청 사항 등)를 명사형 종결어미(~요청, ~예정, ~진행 등)로 상세히 작성

# 📎 첨부파일 및 미디어 분석
- 언급된 파일이나 공유된 이미지 이름 및 OCR/이미지 분석 내용 요약

[주의사항]
- 템플릿에 명시된 내용 외에 불필요한 시스템 메시지나 지시어를 결과물 본문에 출력하지 마세요.
- 절대로 똑같은 문장을 반복해서 생성하지 말고, 작성이 끝나면 즉시 종료하세요.
"""

def encode_image(image_path: Path) -> str:
    with open(image_path, "rb") as image_file:
        return base64.b64encode(image_file.read()).decode('utf-8')

def get_media_type(suffix: str) -> str:
    s = suffix.lower()
    if s in ['.jpg', '.jpeg']:
        return "image/jpeg"
    elif s == '.png':
        return "image/png"
    elif s == '.webp':
        return "image/webp"
    return "image/jpeg"

def generate_journal_markdown(partner: str, date_str: str, chat_text: str, links_text: str, doc_list: list[str], media_paths: list[Path]) -> str:
    docs_str = "\n".join([f"- {f}" for f in doc_list]) if doc_list else "없음"
    media_str = "\n".join([f"- {m.name}" for m in media_paths]) if media_paths else "없음"
    
    text_prompt = f"""
다음은 {date_str} 일자의 '{partner}' 거래처와의 소통 내역입니다.

[대화록]
{chat_text}

[공유된 링크]
{links_text if links_text else '없음'}

[다운로드된 문서 파일]
{docs_str}

[첨부된 이미지 파일 목록]
{media_str}

위 대화 내용과 첨부된 이미지를 꼼꼼히 살펴보고 분석하여 업무 일지를 작성해 주세요.
"""

    content_array = [{"type": "text", "text": text_prompt}]
    
    for mpath in media_paths:
        if mpath.suffix.lower() in ['.jpeg', '.jpg', '.png', '.webp']:
            base64_img = encode_image(mpath)
            media_type = get_media_type(mpath.suffix)
            content_array.append({
                "type": "image",
                "source": {
                    "type": "base64",
                    "media_type": media_type,
                    "data": base64_img
                }
            })

    response = client.messages.create(
        model="claude-sonnet-4-6",
        max_tokens=2048,
        temperature=0.1,
        system=SYSTEM_PROMPT.format(date=date_str, partner=partner),
        messages=[
            {"role": "user", "content": content_array}
        ]
    )
    
    return response.content[0].text
