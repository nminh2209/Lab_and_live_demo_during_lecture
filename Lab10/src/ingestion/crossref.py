from __future__ import annotations

from dataclasses import asdict, dataclass
from pathlib import Path
import re
import time

import requests

from core.config import Settings
from core.utils import compact_join, normalize_whitespace, read_json, write_json

CROSSREF_API_URL = "https://api.crossref.org/works"


@dataclass(frozen=True)
class PaperRecord:
    paper_id: str
    title: str
    summary: str
    authors: list[str]
    categories: list[str]
    primary_category: str
    published: str
    updated: str
    abs_url: str
    pdf_url: str
    comment: str


def _strip_jats_xml(text: str) -> str:
    cleaned = re.sub(r"<[^>]+>", " ", text)
    return normalize_whitespace(cleaned)


def _parse_date(item: dict, keys: list[str]) -> str:
    for key in keys:
        date_parts = item.get(key, {}).get("date-parts", [[]])
        if date_parts and date_parts[0]:
            parts = [str(part) for part in date_parts[0]]
            while len(parts) < 3:
                parts.append("01")
            return "-".join(parts[:3])
    return ""


def _author_name(author: dict) -> str:
    given = author.get("given", "")
    family = author.get("family", "")
    literal = author.get("name", "")
    if literal:
        return normalize_whitespace(literal)
    return normalize_whitespace(f"{given} {family}".strip())


def parse_crossref_payload(payload: dict) -> list[PaperRecord]:
    items = payload.get("message", {}).get("items", [])
    records: list[PaperRecord] = []

    for item in items:
        paper_id = normalize_whitespace(item.get("DOI", ""))
        title_list = item.get("title", [])
        title = normalize_whitespace(title_list[0]) if title_list else ""

        abstract = item.get("abstract", "")
        summary = _strip_jats_xml(abstract) if abstract else ""

        authors = [_author_name(author) for author in item.get("author", [])]
        authors = [author for author in authors if author]

        categories = [normalize_whitespace(subject) for subject in item.get("subject", []) if subject]
        primary_category = categories[0] if categories else "uncategorized"

        published = _parse_date(item, ["published-print", "published-online", "created"])
        updated = _parse_date(item, ["indexed", "content-updated", "updated"])

        abs_url = f"https://doi.org/{paper_id}" if paper_id else ""
        pdf_url = ""
        for link in item.get("link", []):
            if link.get("content-type") == "application/pdf":
                pdf_url = link.get("URL", "")
                break

        subtitle_list = item.get("subtitle", [])
        comment = normalize_whitespace(subtitle_list[0]) if subtitle_list else ""

        if not paper_id or not title:
            continue

        records.append(
            PaperRecord(
                paper_id=paper_id,
                title=title,
                summary=summary,
                authors=authors,
                categories=categories,
                primary_category=primary_category,
                published=published,
                updated=updated or published,
                abs_url=abs_url,
                pdf_url=pdf_url,
                comment=comment,
            )
        )

    return records


def fetch_source_records(settings: Settings) -> list[PaperRecord]:
    params = {
        "query": settings.source_query,
        "filter": settings.source_filter,
        "rows": settings.max_results,
        "select": (
            "DOI,title,subtitle,abstract,author,subject,"
            "published-print,published-online,created,indexed,link"
        ),
    }
    headers = {"User-Agent": "day10-data-observability-lab/1.0 (mailto:student@example.com)"}

    response = None
    for attempt in range(5):
        response = requests.get(CROSSREF_API_URL, params=params, headers=headers, timeout=60)
        if response.status_code in {429, 503}:
            time.sleep(2**attempt)
            continue
        response.raise_for_status()
        break

    if response is None:
        raise RuntimeError("Failed to fetch Crossref records.")

    payload = response.json()
    settings.paths.raw_api_response.parent.mkdir(parents=True, exist_ok=True)
    write_json(settings.paths.raw_api_response, payload)

    records = parse_crossref_payload(payload)
    write_json(settings.paths.raw_records_json, [asdict(record) for record in records])
    return records


def load_raw_records(path: Path) -> list[PaperRecord]:
    payload = read_json(path)
    return [PaperRecord(**item) for item in payload]
