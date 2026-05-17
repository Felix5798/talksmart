from __future__ import annotations

from dataclasses import dataclass

from langchain_text_splitters import MarkdownHeaderTextSplitter, RecursiveCharacterTextSplitter


@dataclass(frozen=True)
class TextChunk:
    index: int
    text: str
    section: str


_HEADERS = [
    ("#", "h1"),
    ("##", "h2"),
    ("###", "h3"),
]


def _section_from_metadata(meta: dict) -> str:
    for key in ("h3", "h2", "h1"):
        if meta.get(key):
            return str(meta[key])
    return "正文"


def chunk_markdown(
    content: str,
    *,
    chunk_size: int = 500,
    chunk_overlap: int = 80,
) -> list[TextChunk]:
    """Split markdown by headers, then merge/split to target chunk size."""
    md_splitter = MarkdownHeaderTextSplitter(headers_to_split_on=_HEADERS)
    header_docs = md_splitter.split_text(content)

    char_splitter = RecursiveCharacterTextSplitter(
        chunk_size=chunk_size,
        chunk_overlap=chunk_overlap,
        separators=["\n\n", "\n", "。", "；", " ", ""],
    )

    pieces: list[tuple[str, str]] = []
    for doc in header_docs:
        section = _section_from_metadata(doc.metadata)
        text = doc.page_content.strip()
        if not text:
            continue
        if len(text) <= chunk_size:
            pieces.append((section, text))
        else:
            for part in char_splitter.split_text(text):
                part = part.strip()
                if part:
                    pieces.append((section, part))

    if not pieces and content.strip():
        for part in char_splitter.split_text(content.strip()):
            part = part.strip()
            if part:
                pieces.append(("正文", part))

    return [TextChunk(index=i, text=text, section=section) for i, (section, text) in enumerate(pieces)]
