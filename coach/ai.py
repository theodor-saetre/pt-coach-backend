"""
AI-COACHEN – setter sammen reglene og Claude.

Slik går det til når appen ber om en ukeplan:
  1. Regelmotoren regner ut de faste tallene (fakta).
  2. Claude får instruksen, brukeren og fakta, og svarer med en plan i fast format.
  3. Kontrollen sjekker planen mot reglene. Er noe feil, får Claude feilene og prøver igjen.
  4. Koden legger på dagsmålene for mat.

Dette kalles ofte en «arbeidsflyt»: koden bestemmer stegene, og AI-en gjør én jobb i dem.
Senere kan du gjøre den til en agent som selv velger hvilke verktøy (regler) den bruker,
f.eks. i coach-chatten.
"""

from __future__ import annotations

import copy
import json
import os
from pathlib import Path

from .planformat import PLAN_SKJEMA
from .regler import beregn_fakta
from .sjekk import legg_til_kosthold, sjekk_plan
from .uten_ai import lag_plan_uten_ai

INSTRUKS = (Path(__file__).parent / "instruks.md").read_text(encoding="utf-8")
STANDARD_MODELL = "claude-sonnet-5-5"
MAKS_FORSOK = 3


def _uten_persondata(bilde: dict) -> dict:
    """Fjern navn og annet AI-en ikke trenger. Personvern: send minst mulig."""
    b = copy.deepcopy(bilde)
    for felt in ("navn", "epost", "telefon"):
        b.get("bruker", {}).pop(felt, None)
    return b


def _melding(bilde: dict, fakta: dict) -> str:
    data = _uten_persondata(bilde)
    return (
        "Lag ukeplanen for denne brukeren.\n\n"
        "<bruker>\n" + json.dumps(data["bruker"], ensure_ascii=False, indent=2) + "\n</bruker>\n\n"
        "<historikk>\n" + json.dumps({k: v for k, v in data.items() if k != "bruker"}, ensure_ascii=False, indent=2)
        + "\n</historikk>\n\n"
        "<fakta>\n" + json.dumps(fakta, ensure_ascii=False, indent=2) + "\n</fakta>"
    )


def _spor_claude(klient, modell: str, meldinger: list[dict]) -> tuple[dict, str]:
    svar = klient.messages.create(
        model=modell,
        max_tokens=6000,
        system=INSTRUKS,
        messages=meldinger,
        output_config={"format": {"type": "json_schema", "schema": PLAN_SKJEMA}},
    )
    tekst = next(b.text for b in svar.content if b.type == "text")
    return json.loads(tekst), tekst


def lag_ukeplan(bilde: dict, uten_ai: bool = False, modell: str | None = None) -> dict:
    """
    Hovedfunksjonen. Tar inn brukerbildet (se docs/avtale.md) og returnerer:
      {"plan": ..., "fakta": ..., "forsok": n, "feil_underveis": [...], "godkjent": bool, "modell": "..."}
    """
    fakta = beregn_fakta(bilde)

    if uten_ai:
        plan = lag_plan_uten_ai(fakta, bilde["bruker"])
        feil = sjekk_plan(plan, fakta)
        return {"plan": legg_til_kosthold(plan, fakta), "fakta": fakta, "forsok": 1,
                "feil_underveis": [feil] if feil else [], "godkjent": not feil, "modell": "uten AI (bare regler)"}

    import anthropic  # importeres bare når AI-en faktisk brukes

    modell = modell or os.getenv("MODELL", STANDARD_MODELL)
    klient = anthropic.Anthropic()  # leser ANTHROPIC_API_KEY fra miljøet / .env
    meldinger = [{"role": "user", "content": _melding(bilde, fakta)}]
    feil_underveis: list[list[str]] = []

    plan: dict = {}
    for forsok in range(1, MAKS_FORSOK + 1):
        plan, tekst = _spor_claude(klient, modell, meldinger)
        feil = sjekk_plan(plan, fakta)
        if not feil:
            return {"plan": legg_til_kosthold(plan, fakta), "fakta": fakta, "forsok": forsok,
                    "feil_underveis": feil_underveis, "godkjent": True, "modell": modell}
        feil_underveis.append(feil)
        # Gi Claude feilene og be om en ny plan
        meldinger += [
            {"role": "assistant", "content": tekst},
            {"role": "user", "content": "Planen bryter disse reglene:\n- " + "\n- ".join(feil)
                                        + "\n\nLag hele planen på nytt og rett alle feilene."},
        ]

    # Ikke godkjent etter alle forsøk: returner, men merk den. Appen skal da vise en enkel reserveplan.
    return {"plan": legg_til_kosthold(plan, fakta), "fakta": fakta, "forsok": MAKS_FORSOK,
            "feil_underveis": feil_underveis, "godkjent": False, "modell": modell}
