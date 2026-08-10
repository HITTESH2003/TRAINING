"""Step 5: combine per-region markdown fragments, in reading order, into one document."""

from __future__ import annotations


def build_page_markdown(page_num: int, region_results: list[dict]) -> str:
    parts = [f"\n\n<!-- page {page_num} -->\n\n"]
    for r in region_results:
        if r.get("markdown"):
            parts.append(r["markdown"])
    return "".join(parts)


def build_document_markdown(title: str, page_markdowns: list[str]) -> str:
    header = f"# {title}\n"
    return header + "".join(page_markdowns) + "\n"
