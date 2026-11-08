"""Initialize the local showcase without exposing credentials to logs."""

import sys
from pathlib import Path

root = Path(__file__).resolve().parents[1]
sys.path[:0] = [str(root), str(root / "backend")]
from dotenv import load_dotenv

load_dotenv(root / ".env")
from app.operations.store import Store

if __name__ == "__main__":
    store = Store()
    if not (root / ".env").exists():
        (root / ".env").write_text(
            "AEGIS_PROVIDER=auto\nGROQ_API_KEY=\nGROQ_MODEL=openai/gpt-oss-120b\nOPENAI_API_KEY=\nOPENAI_MODEL=\n",
            encoding="utf-8",
        )
    print("Workspace initialized with synthetic data.")
    print(f"Local credentials: {store.directory / 'credentials.json'}")
    print(
        "Set GROQ_API_KEY in .env for live Groq planning, or select offline mode explicitly."
    )
    print("Start: python run_server.py")
