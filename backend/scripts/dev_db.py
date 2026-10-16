"""Start a local PostgreSQL server for development without Docker (uses `pgserver`).

Usage: `uv run python scripts/dev_db.py [start|stop] [--write-env]`. Data lives in
`backend/.devdata/pg` and the server keeps running in the background until stopped.
On Windows the port changes on every start; `--write-env` updates DATABASE_URL in `.env`.
"""

import re
import sys
from pathlib import Path

import pgserver

BACKEND_DIR = Path(__file__).resolve().parent.parent
DATA_DIR = BACKEND_DIR / ".devdata" / "pg"
ENV_FILE = BACKEND_DIR / ".env"
DB_NAME = "ai_playground"


def main() -> None:
    """Start (default) or stop the development database."""
    args = [a for a in sys.argv[1:] if not a.startswith("--")]
    command = args[0] if args else "start"
    DATA_DIR.mkdir(parents=True, exist_ok=True)
    server = pgserver.get_server(DATA_DIR, cleanup_mode=None)
    if command == "stop":
        server.cleanup()
        print("Development database stopped.")
        return
    # DB_NAME is a hardcoded constant, not user input.
    exists = server.psql(f"SELECT 1 FROM pg_database WHERE datname = '{DB_NAME}';")  # noqa: S608
    if "(1 row)" not in exists:
        server.psql(f"CREATE DATABASE {DB_NAME};")
    uri = server.get_uri(DB_NAME).replace("postgresql://", "postgresql+asyncpg://", 1)
    print(f"DATABASE_URL={uri}")
    if "--write-env" in sys.argv and ENV_FILE.exists():
        text = ENV_FILE.read_text(encoding="utf-8")
        text = re.sub(r"(?m)^DATABASE_URL=.*$", f"DATABASE_URL={uri}", text)
        ENV_FILE.write_text(text, encoding="utf-8")
        print(f"Updated {ENV_FILE}")


if __name__ == "__main__":
    main()
