"""SQLite schema for research works and their local assets."""

import sqlite3
import uuid
from pathlib import Path
from typing import Union

PAPERHUB_APPLICATION_ID = 0x50485542


def open_store(path: Union[str, Path]) -> sqlite3.Connection:
    """Open an index and create its initial schema without replacing existing data."""
    db = sqlite3.connect(path)
    try:
        application_id = db.execute("PRAGMA application_id").fetchone()[0]
        existing_tables = db.execute(
            "SELECT name FROM sqlite_master WHERE type = 'table' AND name NOT LIKE 'sqlite_%'"
        ).fetchall()
        if application_id != PAPERHUB_APPLICATION_ID and (application_id != 0 or existing_tables):
            raise ValueError("selected SQLite file is not a PaperHub index")
        db.execute("PRAGMA foreign_keys = ON")
        db.executescript(
            """BEGIN;
        CREATE TABLE IF NOT EXISTS work (
            id TEXT PRIMARY KEY,
            kind TEXT NOT NULL,
            title TEXT,
            author TEXT,
            year INTEGER,
            doi TEXT,
            url TEXT
        );
        CREATE TABLE IF NOT EXISTS asset (
            id TEXT PRIMARY KEY,
            path TEXT NOT NULL UNIQUE,
            original_path TEXT,
            size INTEGER NOT NULL CHECK (size >= 0),
            md5 TEXT NOT NULL,
            sha256 TEXT NOT NULL,
            mtime_ns INTEGER,
            format TEXT,
            status TEXT
        );
        CREATE TABLE IF NOT EXISTS work_asset (
            work_id TEXT NOT NULL REFERENCES work(id),
            asset_id TEXT NOT NULL REFERENCES asset(id),
            role TEXT NOT NULL,
            PRIMARY KEY (work_id, asset_id, role)
        );
        CREATE TABLE IF NOT EXISTS zotero_link (
            work_id TEXT NOT NULL REFERENCES work(id),
            library_id TEXT NOT NULL,
            item_key TEXT NOT NULL,
            attachment_key TEXT,
            PRIMARY KEY (library_id, item_key)
        );
        PRAGMA application_id = 1346917698;
        COMMIT;
        """
        )
    except Exception:
        db.rollback()
        db.close()
        raise
    return db


def add_work(db: sqlite3.Connection, kind: str, title=None, work_id=None) -> str:
    """Insert a citable work and return its stable ID."""
    work_id = work_id or str(uuid.uuid4())
    db.execute("INSERT INTO work (id, kind, title) VALUES (?, ?, ?)", (work_id, kind, title))
    return work_id


def add_asset(
    db: sqlite3.Connection, path: str, size: int, md5: str, sha256: str, asset_id=None
) -> str:
    """Insert a local file without merging distinct source paths."""
    asset_id = asset_id or str(uuid.uuid4())
    db.execute(
        "INSERT INTO asset (id, path, size, md5, sha256) VALUES (?, ?, ?, ?, ?)",
        (asset_id, path, size, md5, sha256),
    )
    return asset_id


def link_asset(db: sqlite3.Connection, work_id: str, asset_id: str, role: str) -> None:
    """Attach one physical file to one citable work."""
    db.execute(
        "INSERT INTO work_asset (work_id, asset_id, role) VALUES (?, ?, ?)",
        (work_id, asset_id, role),
    )


def link_zotero(db: sqlite3.Connection, work_id: str, library_id: str, item_key: str) -> None:
    """Record a Zotero item key within its library."""
    db.execute(
        "INSERT INTO zotero_link (work_id, library_id, item_key) VALUES (?, ?, ?)",
        (work_id, library_id, item_key),
    )
