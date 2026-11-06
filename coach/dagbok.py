"""
TRENINGSDAGBOK – AI-parser.

Tar fri tekst fra brukeren og strukturerer det til en treningsøkt.
"""

from __future__ import annotations

import json
import os
import uuid
from datetime import date
from pathlib import Path

OKT_TYPER = ["lop", "styrke", "sykkel", "padel", "fotball", "gange", "annet"]

OKT_SKJEMA = {
    "type": "object",
    "properties": {
        "type": {
            "type": "string",
            "enum": OKT_TYPER,
            "description": "Treningstype. Velg 'annet' hvis usikkert.",
        },
        "tittel": {
            "type": "string",
            "description": "Kort tittel, f.eks. 'Rolig løp' eller 'Styrkeøkt bein'.",
        },
        "minutter": {
            "type": "integer",
            "description": "Varighet i minutter. 0 hvis ikke nevnt.",
        },
        "km": {
            "type": "number",
            "description": "Distanse i km for kondisjon. 0 hvis ikke nevnt eller ikke relevant.",
        },
        "intensitet": {
            "type": "string",
            "enum": ["rolig", "moderat", "hard"],
            "description": "Intensitet på økta.",
        },
        "rpe": {
            "type": "integer",
            "description": "Opplevd anstrengelse 1–10. 0 hvis ikke nevnt.",
        },
        "noter": {
            "type": "string",
            "description": "1–2 vennlige setninger som oppsummerer det brukeren sa.",
        },
        "ovelser": {
            "type": "array",
            "description": "Enkeltøvelser for styrkeøkt. Tom liste for kondisjon.",
            "items": {
                "type": "object",
                "properties": {
                    "navn": {"type": "string", "description": "Navn på øvelsen, f.eks. 'Benkpress'."},
                    "sett": {"type": "integer", "description": "Antall sett. 0 hvis ikke nevnt."},
                    "reps": {"type": "integer", "description": "Reps per sett. 0 hvis ikke nevnt."},
                    "vekt_kg": {"type": "number", "description": "Vekt i kg. 0 hvis ikke nevnt."},
                    "notat": {"type": "string", "description": "Kort notat om øvelsen."},
                },
                "required": ["navn", "sett", "reps", "vekt_kg", "notat"],
                "additionalProperties": False,
            },
        },
    },
    "required": ["type", "tittel", "minutter", "km", "intensitet", "rpe", "noter", "ovelser"],
    "additionalProperties": False,
}

INSTRUKS = (
    "Du er en treningsassistent i en norsk treningsapp. Brukeren beskriver en treningsøkt fritt. "
    "Tolk teksten og fyll ut feltene. Vær tro mot det brukeren sier. "
    "Bruk 0 for minutter, km og rpe hvis de ikke er nevnt. "
    "'noter' er en kort, vennlig oppsummering på norsk (1–2 setninger). "
    "'ovelser' er liste over enkeltøvelser for styrketrening – trekk ut navn, sett, reps og vekt. Tom liste for løp og kondisjon."
)

DAGBOK_FIL = Path(__file__).parent.parent / "dagbok.json"


def les_okter() -> list[dict]:
    if not DAGBOK_FIL.exists():
        return []
    return json.loads(DAGBOK_FIL.read_text(encoding="utf-8"))


def lagre_okt(okt: dict) -> dict:
    okter = les_okter()
    okt["id"] = str(uuid.uuid4())
    okter.append(okt)
    DAGBOK_FIL.write_text(json.dumps(okter, ensure_ascii=False, indent=2), encoding="utf-8")
    return okt


def _kall_ai(tekst: str) -> dict:
    import anthropic
    from .ai import STANDARD_MODELL

    svar = anthropic.Anthropic().messages.create(
        model=os.getenv("MODELL", STANDARD_MODELL),
        max_tokens=1000,
        system=INSTRUKS,
        messages=[{"role": "user", "content": tekst}],
        output_config={"format": {"type": "json_schema", "schema": OKT_SKJEMA}},
    )
    return json.loads(next(b.text for b in svar.content if b.type == "text"))


def parse_okt_bare(tekst: str, dato: str | None = None) -> dict:
    """Parser fri tekst til strukturert økt uten å lagre."""
    okt = _kall_ai(tekst)
    okt["dato"] = dato or str(date.today())
    okt["original_tekst"] = tekst
    return okt


def parse_okt(tekst: str, dato: str | None = None) -> dict:
    """Parser fri tekst til strukturert økt og lagrer den."""
    okt = _kall_ai(tekst)
    okt["dato"] = dato or str(date.today())
    okt["original_tekst"] = tekst
    return lagre_okt(okt)
