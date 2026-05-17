#!/usr/bin/env python
"""Launch Chainlit UI for remote Chroma.

From `backend/`:

    python run/run_chroma_ui.py
"""

from __future__ import annotations

import os
import subprocess
import sys
from pathlib import Path

_BACKEND = Path(__file__).resolve().parent.parent
_VIEWER = _BACKEND / "ui" / "chroma_viewer.py"


def main() -> int:
    env = os.environ.copy()
    # Chainlit 读到 DATABASE_URL 会误启 Postgres data layer；启动前临时移除（业务仍从 .env 经 pydantic 加载）
    env.pop("DATABASE_URL", None)
    env.pop("LITERAL_API_KEY", None)

    cmd = [
        sys.executable,
        "-m",
        "chainlit",
        "run",
        str(_VIEWER),
        "--host",
        "127.0.0.1",
        "--port",
        "8501",
    ]
    return subprocess.call(cmd, cwd=str(_BACKEND), env=env)


if __name__ == "__main__":
    raise SystemExit(main())
