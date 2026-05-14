"""
Legacy entrypoint. Run the API from `backend/`:

  cd backend
  $env:PYTHONPATH = (Resolve-Path .).Path   # PowerShell
  python -m uvicorn api.main:app --reload --host 0.0.0.0 --port 8100

See README.md.
"""

if __name__ == "__main__":
    raise SystemExit(
        "Start the server from the backend folder. See README.md (uvicorn api.main:app)."
    )
