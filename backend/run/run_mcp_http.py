"""
Start commerce MCP on Streamable HTTP (default 127.0.0.1:8200, path /mcp).

From `backend/`:

  python run/run_mcp_http.py

Run alongside the FastAPI API (8100); chat graph calls this URL via MCP_STREAMABLE_HTTP_URL.
"""

from __future__ import annotations

import sys
from pathlib import Path

_BACKEND = Path(__file__).resolve().parent.parent
if str(_BACKEND) not in sys.path:
    sys.path.insert(0, str(_BACKEND))

from mcp_service.commerce_mcp import commerce_mcp

if __name__ == "__main__":
    commerce_mcp.run(transport="streamable-http")
