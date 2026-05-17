#!/usr/bin/env python
"""Ingest a markdown knowledge doc into remote Chroma.

Usage (from backend/, with venv active):

    $env:PYTHONPATH = (Resolve-Path .).Path
    python run/run_kb_pipeline.py

Optional:

    python run/run_kb_pipeline.py --file kb/samples/return_policy.md
"""

from __future__ import annotations

import argparse
import asyncio
import sys
from pathlib import Path

_BACKEND = Path(__file__).resolve().parent.parent
if str(_BACKEND) not in sys.path:
    sys.path.insert(0, str(_BACKEND))

from config import get_settings
from kb.ingest import ingest_markdown_file
from kb.vector_store import VectorStore

_DEFAULT_FILE = _BACKEND / "kb" / "samples" / "return_policy.md"


async def main() -> int:
    parser = argparse.ArgumentParser(description="KB ingest into remote Chroma")
    parser.add_argument(
        "--file",
        type=Path,
        default=_DEFAULT_FILE,
        help="Markdown file to ingest",
    )
    parser.add_argument("--doc-id", default="return_policy", help="Document id in Chroma")
    parser.add_argument("--title", default="退货政策", help="Document title metadata")
    args = parser.parse_args()

    try:
        settings = get_settings()
    except Exception as exc:
        print(f"错误: 配置加载失败 ({exc})", file=sys.stderr)
        print("请在 backend/.env 中配置 CHROMA_URL 等变量", file=sys.stderr)
        return 1

    if not settings.dashscope_api_key:
        print("错误: 请在 backend/.env 中配置 DASHSCOPE_API_KEY", file=sys.stderr)
        return 1

    md_path = args.file if args.file.is_absolute() else _BACKEND / args.file
    if not md_path.is_file():
        print(f"错误: 文件不存在 {md_path}", file=sys.stderr)
        return 1

    print(f"Chroma: {settings.chroma_url}")
    print(f"Collection: {settings.chroma_collection}")
    print(f"入库文件: {md_path}")

    result = await ingest_markdown_file(
        md_path,
        doc_id=args.doc_id,
        title=args.title,
        doc_type="return_policy",
        settings=settings,
    )
    store = VectorStore(settings)
    print(
        f"\n入库完成: doc_id={result.doc_id}, chunks={result.chunk_count}, "
        f"collection={result.collection}, total_vectors={store.count}"
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(asyncio.run(main()))
