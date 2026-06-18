import csv
import re
from datetime import date, datetime
from pathlib import Path


def parse_kakao_csv(path: Path) -> list[dict]:
    rows = []
    with open(path, encoding="utf-8-sig", newline="") as f:
        reader = csv.DictReader(f)
        for row in reader:
            try:
                row["datetime"] = datetime.strptime(row["Date"], "%Y-%m-%d %H:%M:%S")
            except (ValueError, KeyError):
                continue
            rows.append(row)
    return rows


def group_by_date(rows: list[dict]) -> dict[date, list[dict]]:
    groups = {}
    for r in rows:
        d = r["datetime"].date()
        if d not in groups:
            groups[d] = []
        groups[d].append(r)
    return groups


def extract_file_refs(rows: list[dict]) -> list[str]:
    pattern = re.compile(r"^파일:\s*(.+)$")
    files = []
    for row in rows:
        m = pattern.match(row.get("Message", "").strip())
        if m:
            files.append(m.group(1).strip())
    return files


def extract_links(rows: list[dict]) -> list[str]:
    links = []
    url_pattern = re.compile(r"(https?://[^\s]+)")
    for row in rows:
        msg = row.get("Message", "")
        matches = url_pattern.findall(msg)
        for match in matches:
            if match not in links:
                links.append(match)
    return links


def format_as_txt(rows: list[dict]) -> str:
    lines = []
    for row in rows:
        time_str = row["datetime"].strftime("%H:%M")
        lines.append(f"[{time_str}] {row['User']}: {row['Message']}")
    return "\n".join(lines)
