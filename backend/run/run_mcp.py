"""
Run commerce MCP over stdio (e.g. Cursor). Tool definitions live in `mcp_service.commerce_mcp`.

Usage (from `backend/`):

  python run/run_mcp.py

For HTTP MCP on port 8200 (used by the chat API), use `python run/run_mcp_http.py` instead.
"""

from __future__ import annotations

import sys
from pathlib import Path

_BACKEND = Path(__file__).resolve().parent.parent
if str(_BACKEND) not in sys.path:
    sys.path.insert(0, str(_BACKEND))

from mcp_service.commerce_mcp import commerce_mcp

if __name__ == "__main__":
    commerce_mcp.run()
