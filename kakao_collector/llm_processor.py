import os
from anthropic import Anthropic
from dotenv import load_dotenv

load_dotenv()

SYSTEM_PROMPT = """
당신은 B2B 거래처 관리 및 업무 일지 작성을 돕는 전문 AI 비서입니다.
주어진 거래처 대화록과 파일/링크 목록을 바탕으로 간결하고 명확한 마크다운 형식의 업무 일지를 작성해야 합니다.

[작성 규칙]
1. 문체: "~함", "~예정", "~요청됨"과 같은 간결한 개조식을 사용합니다.
2. 출력 형식: 아래 제공된 템플릿 구조를 반드시 따릅니다. YAML Front Matter를 포함해야 합니다.
3. 정보 추출: 위탁 배송지, 송장 번호, 입고 리스트, 재고 변동, 할인 등의 중요 정보를 빠짐없이 요약합니다.

[템플릿]
---
title: "{date} {partner} 업무 일지"
date: {date}
partner: "{partner}"
tags: [업무일지, {partner}]
---

# 📋 요약
- (핵심 요약 1)
- (핵심 요약 2)

# ✅ 할 일 (Action Items)
- [ ] (추출된 일정이나 해야 할 일. 없으면 "해당 없음" 기재)
- [ ] 

# 📎 첨부파일 및 미디어
- (언급된 파일이나 공유된 이미지, 링크 등 나열)

# ❓ 미해결 이슈
- (대화 내용 중 아직 결론나지 않았거나 확인이 필요한 사항. 없으면 "해당 없음")

# 💬 주요 대화 상세
- (필요한 경우 중요한 대화 내역이나 고객 주소/송장 등 상세 데이터 기록)
"""

def generate_journal_markdown(partner: str, date_str: str, chat_text: str, links_text: str, files_list: list[str]) -> str:
    client = Anthropic(api_key=os.getenv("ANTHROPIC_API_KEY"))
    
    files_str = "\n".join([f"- {f}" for f in files_list]) if files_list else "없음"
    
    user_prompt = f"""
다음은 {date_str} 일자의 '{partner}' 거래처와의 소통 내역입니다.

[대화록]
{chat_text}

[공유된 링크]
{links_text if links_text else '없음'}

[다운로드된 파일 및 미디어]
{files_str}

위 내용을 바탕으로 업무 일지를 작성해 주세요.
"""

    response = client.messages.create(
        model="claude-3-5-sonnet-20241022",
        max_tokens=2048,
        system=SYSTEM_PROMPT.format(date=date_str, partner=partner),
        messages=[
            {"role": "user", "content": user_prompt}
        ]
    )
    
    return response.content[0].text
