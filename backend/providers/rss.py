"""RSS / Atom news provider. Stores only headline, metadata, a short excerpt and link."""
from __future__ import annotations

import hashlib
import html
import re
import time
import xml.etree.ElementTree as ET
from email.utils import parsedate_to_datetime
from datetime import datetime
from typing import Any

from backend.models.schemas import NewsItem
from backend.utils import http

_TAG = re.compile(r"<[^>]+>")
_WS = re.compile(r"\s+")
NS = {"media": "http://search.yahoo.com/mrss/", "atom": "http://www.w3.org/2005/Atom", "dc": "http://purl.org/dc/elements/1.1/"}


def strip_html(s: str | None, limit: int = 280) -> str | None:
    if not s:
        return None
    t = html.unescape(_TAG.sub(" ", html.unescape(s)))
    t = _WS.sub(" ", t).strip()
    if len(t) > limit:
        t = t[:limit].rsplit(" ", 1)[0] + "…"
    return t or None


def _parse_date(s: str | None) -> float | None:
    if not s:
        return None
    s = s.strip()
    try:
        return parsedate_to_datetime(s).timestamp()
    except (TypeError, ValueError, IndexError):
        pass
    for fmt in ("%Y-%m-%dT%H:%M:%S%z", "%Y-%m-%dT%H:%M:%SZ", "%Y-%m-%dT%H:%M:%S.%f%z", "%Y-%m-%d"):
        try:
            dt = datetime.strptime(s.replace("Z", "+0000") if fmt.endswith("%z") else s, fmt)
            return dt.timestamp()
        except ValueError:
            continue
    try:
        return datetime.fromisoformat(s.replace("Z", "+00:00")).timestamp()
    except ValueError:
        return None


def item_id(url: str, title: str) -> str:
    return hashlib.sha1((url or title).encode("utf-8", "ignore")).hexdigest()[:16]


class RSSProvider:
    name = "rss"
    label = "Publisher RSS feeds"

    async def fetch_feed(self, feed: dict[str, Any]) -> list[NewsItem]:
        text = await http.get_text(f"rss:{feed['id']}", feed["url"], timeout=15, retries=0)
        text = text.lstrip("﻿").strip()
        root = ET.fromstring(text.encode("utf-8"))
        now = time.time()
        items: list[NewsItem] = []
        entries = root.findall(".//item") or root.findall(".//atom:entry", NS)
        for e in entries[:60]:
            title = (e.findtext("title") or e.findtext("atom:title", namespaces=NS) or "").strip()
            link = (e.findtext("link") or "").strip()
            if not link:
                le = e.find("atom:link", NS)
                link = le.get("href", "") if le is not None else ""
            if not title or not link:
                continue
            desc = e.findtext("description") or e.findtext("atom:summary", namespaces=NS) or e.findtext("atom:content", namespaces=NS)
            pub = e.findtext("pubDate") or e.findtext("atom:published", namespaces=NS) or e.findtext("atom:updated", namespaces=NS) or e.findtext("dc:date", namespaces=NS)
            thumb = None
            for tag in ("media:thumbnail", "media:content"):
                m = e.find(tag, NS)
                if m is not None and m.get("url") and not m.get("url", "").endswith((".mp4", ".mp3")):
                    thumb = m.get("url")
                    break
            if thumb is None:
                enc = e.find("enclosure")
                if enc is not None and (enc.get("type") or "").startswith("image"):
                    thumb = enc.get("url")
            if not link.startswith(("http://", "https://")):
                continue
            items.append(NewsItem(
                id=item_id(link, title), title=html.unescape(title), url=link, publisher=feed["publisher"],
                published_at=_parse_date(pub) or now, retrieved_at=now, category=feed.get("category"),
                summary=strip_html(desc), thumbnail=thumb if thumb and thumb.startswith("https://") else None, source_feed=feed["id"],
            ))
        return items
