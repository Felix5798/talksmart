"""
Run commerce MCP over stdio (e.g. Cursor). Tool definitions live in `mcp_service.commerce_mcp`.

Usage (from `backend/` directory):

  set PYTHONPATH=.
  python run_mcp.py

For HTTP MCP on port 8200 (used by the chat API), use `python run_mcp_http.py` instead.
"""

from __future__ import annotations

from mcp_service.commerce_mcp import commerce_mcp

if __name__ == "__main__":
    commerce_mcp.run()
