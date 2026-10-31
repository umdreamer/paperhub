"""SQLite schema for research works and their local assets."""

import sqlite3
from pathlib import Path
from typing import Union


def open_store(path: Union[str, Path]) -> sqlite3.Connection:
    """Open an index and create its initial schema without replacing existing data."""
    db = sqlite3.connect(path)
    db.execute("PRAGMA foreign_keys = ON")
    db.executescript(
        """
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
        """
    )
    return db
