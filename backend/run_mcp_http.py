"""
Start commerce MCP on Streamable HTTP (default 127.0.0.1:8200, path /mcp).

From `backend/`:

  set PYTHONPATH=.
  python run_mcp_http.py

Run alongside the FastAPI API (8100); chat graph calls this URL via MCP_STREAMABLE_HTTP_URL.
"""

from __future__ import annotations

from mcp_service.commerce_mcp import commerce_mcp

if __name__ == "__main__":
    commerce_mcp.run(transport="streamable-http")
