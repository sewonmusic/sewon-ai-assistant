import requests
from bs4 import BeautifulSoup

def scrape_link_metadata(url: str) -> dict:
    try:
        headers = {
            "User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36"
        }
        resp = requests.get(url, headers=headers, timeout=5)
        resp.raise_for_status()
        soup = BeautifulSoup(resp.text, "html.parser")
        
        title = soup.title.string if soup.title else ""
        og_title = soup.find("meta", property="og:title")
        if og_title and og_title.get("content"):
            title = og_title.get("content")
            
        desc = ""
        og_desc = soup.find("meta", property="og:description")
        if og_desc and og_desc.get("content"):
            desc = og_desc.get("content")
            
        return {"url": url, "title": title.strip() if title else "제목 없음", "description": desc.strip() if desc else ""}
    except Exception as e:
        print(f"[경고] 메타데이터 크롤링 실패 ({url}): {e}")
        return {"url": url, "title": "접속 불가 또는 메타데이터 없음", "description": ""}

def format_links(links_info: list[dict]) -> str:
    lines = []
    for info in links_info:
        lines.append(f"제목: {info['title']}")
        if info['description']:
            lines.append(f"설명: {info['description']}")
        lines.append(f"링크: {info['url']}\n")
    return "\n".join(lines)
