"""Local signing material. Never use a shared source-code signing secret."""

import os
from pathlib import Path
import secrets


def signing_key(name):
    configured = os.getenv(name)
    if configured:
        return configured.encode()
    directory = Path(
        os.getenv("AEGIS_DATA_DIR") or Path(__file__).resolve().parents[2] / ".local"
    )
    directory.mkdir(parents=True, exist_ok=True)
    path = directory / (name.lower() + ".key")
    try:
        with path.open("x", encoding="utf-8") as f:
            f.write(secrets.token_hex(32))
        path.chmod(0o600)
    except FileExistsError:
        pass
    return path.read_text().strip().encode()
