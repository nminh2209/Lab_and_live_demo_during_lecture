from __future__ import annotations


def parse_policy_markdown(markdown_text: str) -> list[dict]:
    chunks: list[dict] = []
    current_h2: str | None = None
    current_h3: str | None = None
    content_lines: list[str] = []

    def flush_chunk() -> None:
        nonlocal current_h3, content_lines
        if not current_h2 or not current_h3:
            content_lines = []
            return

        content = "\n".join(content_lines).strip()
        if not content:
            content_lines = []
            return

        citation = f"{current_h2} > {current_h3}"
        rendered_text = f"## {current_h2}\n### {current_h3}\n{content}"
        chunks.append(
            {
                "section_h2": current_h2,
                "section_h3": current_h3,
                "citation": citation,
                "rendered_text": rendered_text,
            }
        )
        content_lines = []

    for line in markdown_text.splitlines():
        if line.startswith("### "):
            flush_chunk()
            current_h3 = line[4:].strip()
            content_lines = []
            continue

        if line.startswith("## "):
            flush_chunk()
            current_h2 = line[3:].strip()
            current_h3 = None
            content_lines = []
            continue

        if current_h3 is not None:
            content_lines.append(line)

    flush_chunk()
    return chunks
