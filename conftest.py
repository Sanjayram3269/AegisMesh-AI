"""Never run repository tests against the presenter's persistent workspace."""

import os
from pathlib import Path
import tempfile

test_directory = Path(tempfile.mkdtemp(prefix="aegismesh-test-"))
os.environ["AEGIS_DATA_DIR"] = str(test_directory / "operations")
os.environ["DATABASE_URL"] = "sqlite:///" + str(test_directory / "legacy.db").replace(
    "\\", "/"
)
