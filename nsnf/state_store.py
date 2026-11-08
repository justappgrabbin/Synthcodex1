"""Transactional append-only journal with hash-linked state and content-addressed blobs."""
from pathlib import Path
import hashlib
import json
import sqlite3
from datetime import datetime, timezone
from .schema import canonical, digest


class Store:
    def __init__(self, root):
        self.root = Path(root)
        self.root.mkdir(parents=True, exist_ok=True)
        self.blobs = self.root / "blobs"
        self.blobs.mkdir(exist_ok=True)
        self.db = sqlite3.connect(self.root / "field.sqlite", check_same_thread=False, isolation_level=None)
        self.db.execute("PRAGMA journal_mode=WAL")
        self.db.execute("PRAGMA foreign_keys=ON")
        self.db.executescript('''
        CREATE TABLE IF NOT EXISTS journal (
          seq INTEGER PRIMARY KEY, id TEXT UNIQUE NOT NULL, prior TEXT,
          actor TEXT NOT NULL, kind TEXT NOT NULL, payload TEXT NOT NULL,
          state_hash TEXT NOT NULL, timestamp TEXT NOT NULL);
        CREATE TABLE IF NOT EXISTS artifacts (
          hash TEXT PRIMARY KEY, size INTEGER NOT NULL, media_type TEXT NOT NULL);
        CREATE TRIGGER IF NOT EXISTS no_update BEFORE UPDATE ON journal
          BEGIN SELECT RAISE(ABORT, 'append-only journal'); END;
        CREATE TRIGGER IF NOT EXISTS no_delete BEFORE DELETE ON journal
          BEGIN SELECT RAISE(ABORT, 'append-only journal'); END;
        ''')

    def put_bytes(self, data, media_type="application/octet-stream"):
        key = hashlib.sha256(data).hexdigest()
        path = self.blobs / key
        if not path.exists():
            temporary = self.blobs / (key + ".tmp")
            temporary.write_bytes(data)
            temporary.replace(path)
        self.db.execute("INSERT OR IGNORE INTO artifacts VALUES (?, ?, ?)", (key, len(data), media_type))
        return key

    def get_bytes(self, key):
        if len(key) != 64 or any(c not in "0123456789abcdef" for c in key):
            raise ValueError("invalid artifact hash")
        data = (self.blobs / key).read_bytes()
        if hashlib.sha256(data).hexdigest() != key:
            raise ValueError("artifact integrity failure")
        return data

    def put(self, value):
        return self.put_bytes(canonical(value).encode(), "application/json")

    def get(self, key):
        return json.loads(self.get_bytes(key))

    def latest(self):
        row = self.db.execute("SELECT id, state_hash FROM journal ORDER BY seq DESC LIMIT 1").fetchone()
        return {"id": row[0], "state_hash": row[1], "state": self.get(row[1])} if row else None

    def append(self, actor, kind, payload, state, expected_prior):
        # Transaction rejects competing writers rather than losing their state updates.
        try:
            self.db.execute("BEGIN IMMEDIATE")
            row = self.db.execute("SELECT id FROM journal ORDER BY seq DESC LIMIT 1").fetchone()
            prior = row[0] if row else None
            if prior != expected_prior:
                raise ValueError("concurrent state change; reload and retry")
            state_hash = self.put(state)
            timestamp = datetime.now(timezone.utc).isoformat()
            record = {"prior": prior, "actor": actor, "kind": kind, "payload": payload,
                      "state_hash": state_hash, "timestamp": timestamp}
            key = digest(record)
            self.db.execute("INSERT INTO journal(id, prior, actor, kind, payload, state_hash, timestamp) VALUES (?, ?, ?, ?, ?, ?, ?)",
                            (key, prior, actor, kind, canonical(payload), state_hash, timestamp))
            self.db.commit()
            return key
        except BaseException:
            self.db.rollback()
            raise

    def records(self, actor=None):
        query = "SELECT id, prior, actor, kind, payload, state_hash, timestamp FROM journal"
        rows = self.db.execute(query + (" WHERE actor=?" if actor else "") + " ORDER BY seq", (actor,) if actor else ())
        return [dict(zip(("id", "prior", "actor", "kind", "payload", "state_hash", "timestamp"),
                         (r[0], r[1], r[2], r[3], json.loads(r[4]), r[5], r[6]))) for r in rows]

    def verify(self):
        prior = None
        for row in self.records():
            key = row.pop("id")
            if row["prior"] != prior or digest(row) != key:
                raise ValueError("journal chain verification failed")
            self.get(row["state_hash"])
            prior = key
        return {"valid": True, "records": len(self.records()), "head": prior}
