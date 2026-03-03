#!/usr/bin/env python3
"""
블로그 Atom 피드를 파싱하여 index.html의 블로그 섹션을 자동 업데이트합니다.
외부 의존성 없이 Python 표준 라이브러리만 사용합니다.
"""

import sys
import re
import html
from pathlib import Path
from urllib.request import urlopen, Request
from xml.etree import ElementTree as ET

FEED_URL = "https://blog.wonderx.co.kr/feed"
INDEX_PATH = Path(__file__).resolve().parent.parent / "index.html"
MAX_POSTS = 5
ATOM_NS = "{http://www.w3.org/2005/Atom}"

START_MARKER = "<!-- BLOG_POSTS_START -->"
END_MARKER = "<!-- BLOG_POSTS_END -->"


def fetch_feed():
    """Atom 피드를 가져와 파싱합니다."""
    req = Request(FEED_URL, headers={"User-Agent": "WonderX-Blog-Updater/1.0"})
    with urlopen(req, timeout=30) as resp:
        return ET.parse(resp)


def parse_posts(tree):
    """피드에서 최신 포스트를 추출합니다. 영문 포스트(-en/)는 제외."""
    root = tree.getroot()
    posts = []

    for entry in root.findall(f"{ATOM_NS}entry"):
        link_el = entry.find(f"{ATOM_NS}link[@rel='alternate']")
        if link_el is None:
            continue
        url = link_el.get("href", "")

        title = entry.findtext(f"{ATOM_NS}title", "").strip()
        summary = entry.findtext(f"{ATOM_NS}summary", "").strip()
        published = entry.findtext(f"{ATOM_NS}published", "")

        # 날짜 변환: 2026-02-21T09:00:00+09:00 → 2026.02.21
        date_match = re.match(r"(\d{4})-(\d{2})-(\d{2})", published)
        date_str = f"{date_match.group(1)}.{date_match.group(2)}.{date_match.group(3)}" if date_match else ""

        if title and date_str:
            posts.append({
                "url": url,
                "date": date_str,
                "title": html.escape(title),
                "summary": html.escape(summary),
            })

        if len(posts) >= MAX_POSTS:
            break

    return posts


def generate_html(posts):
    """블로그 카드 HTML을 생성합니다."""
    cards = []
    for post in posts:
        card = (
            f'            <a href="{post["url"]}" class="blog-card" target="_blank" rel="noopener">\n'
            f'                <div class="blog-card-date">{post["date"]}</div>\n'
            f'                <h3>{post["title"]}</h3>\n'
            f'                <p>{post["summary"]}</p>\n'
            f'            </a>'
        )
        cards.append(card)

    return "\n\n".join(cards)


def update_index(new_html):
    """index.html의 마커 사이 콘텐츠를 교체합니다."""
    content = INDEX_PATH.read_text(encoding="utf-8")

    start_idx = content.find(START_MARKER)
    end_idx = content.find(END_MARKER)

    if start_idx == -1 or end_idx == -1:
        print("ERROR: 마커를 찾을 수 없습니다.", file=sys.stderr)
        sys.exit(1)

    before = content[:start_idx + len(START_MARKER)]
    after = content[end_idx:]

    updated = f"{before}\n{new_html}\n            {after}"

    if content == updated:
        print("변경사항 없음. 업데이트 건너뜀.")
        return False

    INDEX_PATH.write_text(updated, encoding="utf-8")
    print("index.html 블로그 섹션 업데이트 완료.")
    return True


def main():
    print(f"피드 가져오는 중: {FEED_URL}")
    tree = fetch_feed()

    print("포스트 파싱 중...")
    posts = parse_posts(tree)
    print(f"  {len(posts)}개 포스트 발견")

    if not posts:
        print("WARNING: 포스트를 찾을 수 없습니다.", file=sys.stderr)
        sys.exit(1)

    for p in posts:
        print(f"  - [{p['date']}] {p['title']}")

    new_html = generate_html(posts)
    changed = update_index(new_html)

    sys.exit(0 if changed else 0)


if __name__ == "__main__":
    main()
