"""
Database – SQLite for flerbrukerstøtte.

Tabeller:
  utovere          – alle utøvere treneren har lagt til
  planlagte_okter  – økter treneren har satt opp for en utøver
  utforte_okter    – økter utøveren har logget (AI-strukturert)
  meldinger        – chat mellom trener og utøver
"""

from __future__ import annotations

import json
import sqlite3
import uuid
from contextlib import contextmanager
from datetime import datetime, timezone
from pathlib import Path

DB_FIL = Path(__file__).resolve().parent.parent / "ptcoach.db"


@contextmanager
def kobling():
    con = sqlite3.connect(DB_FIL)
    con.row_factory = sqlite3.Row
    con.execute("PRAGMA journal_mode=WAL")
    try:
        yield con
        con.commit()
    except Exception:
        con.rollback()
        raise
    finally:
        con.close()


def init_db():
    with kobling() as con:
        con.executescript("""
        CREATE TABLE IF NOT EXISTS utovere (
            id        TEXT PRIMARY KEY,
            navn      TEXT NOT NULL,
            opprettet TEXT NOT NULL
        );

        CREATE TABLE IF NOT EXISTS planlagte_okter (
            id          TEXT PRIMARY KEY,
            utover_id   TEXT NOT NULL REFERENCES utovere(id),
            dato        TEXT NOT NULL,
            type        TEXT NOT NULL,
            tittel      TEXT NOT NULL,
            minutter    INTEGER,
            intensitet  TEXT,
            beskrivelse TEXT,
            opprettet   TEXT NOT NULL
        );

        CREATE TABLE IF NOT EXISTS utforte_okter (
            id            TEXT PRIMARY KEY,
            utover_id     TEXT NOT NULL REFERENCES utovere(id),
            planlagt_id   TEXT REFERENCES planlagte_okter(id),
            dato          TEXT NOT NULL,
            type          TEXT NOT NULL,
            tittel        TEXT NOT NULL,
            minutter      INTEGER,
            km            REAL,
            intensitet    TEXT,
            rpe           INTEGER,
            noter         TEXT,
            original_tekst TEXT,
            opprettet     TEXT NOT NULL
        );

        CREATE TABLE IF NOT EXISTS meldinger (
            id        TEXT PRIMARY KEY,
            utover_id TEXT NOT NULL REFERENCES utovere(id),
            fra       TEXT NOT NULL,
            tekst     TEXT NOT NULL,
            opprettet TEXT NOT NULL
        );
        """)
        try:
            con.execute("ALTER TABLE utforte_okter ADD COLUMN ovelser TEXT DEFAULT '[]'")
        except Exception:
            pass


def _nå() -> str:
    return datetime.now(timezone.utc).isoformat()


def _row_til_dict(row) -> dict:
    return dict(row) if row else None


# ── Utøvere ──────────────────────────────────────────────────────────────────

def hent_alle_utovere() -> list[dict]:
    with kobling() as con:
        rows = con.execute(
            "SELECT * FROM utovere ORDER BY navn"
        ).fetchall()
    return [dict(r) for r in rows]


def opprett_utover(navn: str) -> dict:
    u = {"id": str(uuid.uuid4()), "navn": navn, "opprettet": _nå()}
    with kobling() as con:
        con.execute(
            "INSERT INTO utovere (id, navn, opprettet) VALUES (?, ?, ?)",
            (u["id"], u["navn"], u["opprettet"]),
        )
    return u


def hent_utover(utover_id: str) -> dict | None:
    with kobling() as con:
        row = con.execute(
            "SELECT * FROM utovere WHERE id = ?", (utover_id,)
        ).fetchone()
    return _row_til_dict(row)


# ── Planlagte økter ───────────────────────────────────────────────────────────

def hent_plan(utover_id: str) -> list[dict]:
    with kobling() as con:
        rows = con.execute(
            "SELECT * FROM planlagte_okter WHERE utover_id = ? ORDER BY dato",
            (utover_id,),
        ).fetchall()
    return [dict(r) for r in rows]


def legg_til_planlagt(utover_id: str, data: dict) -> dict:
    okt = {
        "id": str(uuid.uuid4()),
        "utover_id": utover_id,
        "dato": data["dato"],
        "type": data["type"],
        "tittel": data["tittel"],
        "minutter": data.get("minutter"),
        "intensitet": data.get("intensitet"),
        "beskrivelse": data.get("beskrivelse", ""),
        "opprettet": _nå(),
    }
    with kobling() as con:
        con.execute(
            """INSERT INTO planlagte_okter
               (id, utover_id, dato, type, tittel, minutter, intensitet, beskrivelse, opprettet)
               VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)""",
            (okt["id"], okt["utover_id"], okt["dato"], okt["type"],
             okt["tittel"], okt["minutter"], okt["intensitet"],
             okt["beskrivelse"], okt["opprettet"]),
        )
    return okt


def slett_planlagt(okt_id: str) -> bool:
    with kobling() as con:
        n = con.execute(
            "DELETE FROM planlagte_okter WHERE id = ?", (okt_id,)
        ).rowcount
    return n > 0


# ── Utførte økter ─────────────────────────────────────────────────────────────

def hent_logg(utover_id: str) -> list[dict]:
    with kobling() as con:
        rows = con.execute(
            "SELECT * FROM utforte_okter WHERE utover_id = ? ORDER BY dato DESC",
            (utover_id,),
        ).fetchall()
    result = []
    for r in rows:
        d = dict(r)
        d["ovelser"] = json.loads(d.get("ovelser") or "[]")
        result.append(d)
    return result


def logg_utfort(utover_id: str, okt: dict, planlagt_id: str | None = None) -> dict:
    ovelser = okt.get("ovelser", [])
    o = {
        "id": str(uuid.uuid4()),
        "utover_id": utover_id,
        "planlagt_id": planlagt_id,
        "dato": okt.get("dato"),
        "type": okt.get("type"),
        "tittel": okt.get("tittel"),
        "minutter": okt.get("minutter"),
        "km": okt.get("km"),
        "intensitet": okt.get("intensitet"),
        "rpe": okt.get("rpe"),
        "noter": okt.get("noter"),
        "original_tekst": okt.get("original_tekst"),
        "ovelser": ovelser,
        "opprettet": _nå(),
    }
    with kobling() as con:
        con.execute(
            """INSERT INTO utforte_okter
               (id, utover_id, planlagt_id, dato, type, tittel, minutter,
                km, intensitet, rpe, noter, original_tekst, ovelser, opprettet)
               VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)""",
            (o["id"], o["utover_id"], o["planlagt_id"], o["dato"], o["type"],
             o["tittel"], o["minutter"], o["km"], o["intensitet"],
             o["rpe"], o["noter"], o["original_tekst"],
             json.dumps(ovelser, ensure_ascii=False), o["opprettet"]),
        )
    return o


# ── Meldinger ─────────────────────────────────────────────────────────────────

def hent_meldinger(utover_id: str, etter: str | None = None) -> list[dict]:
    with kobling() as con:
        if etter:
            rows = con.execute(
                "SELECT * FROM meldinger WHERE utover_id = ? AND opprettet > ? ORDER BY opprettet",
                (utover_id, etter),
            ).fetchall()
        else:
            rows = con.execute(
                "SELECT * FROM meldinger WHERE utover_id = ? ORDER BY opprettet",
                (utover_id,),
            ).fetchall()
    return [dict(r) for r in rows]


def send_melding(utover_id: str, fra: str, tekst: str) -> dict:
    m = {
        "id": str(uuid.uuid4()),
        "utover_id": utover_id,
        "fra": fra,
        "tekst": tekst,
        "opprettet": _nå(),
    }
    with kobling() as con:
        con.execute(
            "INSERT INTO meldinger (id, utover_id, fra, tekst, opprettet) VALUES (?, ?, ?, ?, ?)",
            (m["id"], m["utover_id"], m["fra"], m["tekst"], m["opprettet"]),
        )
    return m
