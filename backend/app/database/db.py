"""SQLite Database Connection & Session Management."""

import os
from pathlib import Path
from sqlalchemy import create_engine, text
from sqlalchemy.orm import sessionmaker
from .models import Base

# Database file location
data_directory = Path(os.getenv("AEGIS_DATA_DIR") or Path(__file__).resolve().parents[3] / ".local")
data_directory.mkdir(parents=True, exist_ok=True)
DB_PATH = str((data_directory / "legacy.db").resolve())
DATABASE_URL = os.getenv("DATABASE_URL", f"sqlite:///{DB_PATH}")

engine = create_engine(DATABASE_URL, connect_args={"check_same_thread": False})
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

def init_db():
    Base.metadata.create_all(bind=engine)
    with engine.connect() as conn:
        for col, col_type in [
            ("execution_id", "VARCHAR(64)"),
            ("inherent_risk_json", "TEXT"),
            ("final_risk_json", "TEXT"),
            ("risk_reduction", "INTEGER"),
            ("lifecycle_history_json", "TEXT")
        ]:
            try:
                conn.execute(text(f"ALTER TABLE audit_records ADD COLUMN {col} {col_type}"))
                conn.commit()
            except Exception:
                pass

def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()
