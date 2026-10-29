"""
COACH-CHATTEN (første versjon) – brukeren skriver fritt, og coachen forstår dagsformen.

Foreløpig kan chatten én ting: forstå om brukeren er syk, frisk igjen, sliten eller i form,
oppdatere brukerbildet og lage en ny plan. Senere blir den en agent med reglene som verktøy
(se docs/beslutninger.md, neste steg 3).
"""

from __future__ import annotations

import copy
import json
import os

DAGSFORMER = ["syk", "frisk", "sliten", "pigg", "ok", "ingen"]

DAGSFORM_SKJEMA = {
    "type": "object",
    "properties": {
        "dagsform": {
            "type": "string", "enum": DAGSFORMER,
            "description": "syk = syk nå. frisk = frisk igjen etter sykdom. ingen = meldingen handler ikke om dagsform.",
        },
        "svar": {"type": "string", "description": "1–2 korte, vennlige setninger tilbake til brukeren, på norsk."},
    },
    "required": ["dagsform", "svar"],
    "additionalProperties": False,
}

CHAT_INSTRUKS = (
    "Du er PT-en i en norsk treningsapp. Les meldingen fra brukeren og finn dagsformen. "
    "«frisk» betyr at brukeren sier hen er frisk igjen etter sykdom. «syk» betyr at brukeren er syk nå "
    "(feber, forkjølelse, omgangssyke og lignende). Gi ingen medisinske råd. Er meldingen om noe annet, "
    "velg «ingen» og si at chatten foreløpig bare kan oppdatere dagsformen."
)

# Reserve uten AI: enkle stikkord. Rekkefølgen betyr noe («ikke syk» skal bli frisk, «ikke frisk» syk).
STIKKORD = [
    ("frisk", ["ikke syk", "ikke lenger syk"]),
    ("syk", ["ikke frisk", "fortsatt syk", "syk", "feber", "forkjøl", "influensa", "omgangssyke", "covid"]),
    ("frisk", ["frisk", "bedre nå", "er tilbake"]),
    ("sliten", ["sliten", "trøtt", "sov dårlig", "slitne"]),
    ("pigg", ["pigg", "opplagt", "i form"]),
]
SVAR_UTEN_AI = {
    "syk": "God bedring! Jeg setter opp hvile og lager en ny plan.",
    "frisk": "Så bra at du er frisk igjen! Vi starter rolig. Her er den nye planen.",
    "sliten": "Da tar vi det roligere i dag. Her er den nye planen.",
    "pigg": "Flott! Da kjører vi planen som den er.",
    "ok": "Supert, da kjører vi planen som den er.",
    "ingen": "Foreløpig kan chatten bare oppdatere dagsformen din: syk, frisk, sliten eller pigg.",
}


def tolk_melding(tekst: str, uten_ai: bool = False, modell: str | None = None) -> dict:
    """Returnerer {"dagsform": ..., "svar": ...}."""
    if uten_ai:
        liten = tekst.lower()
        form = next((f for f, ord_ in STIKKORD if any(o in liten for o in ord_)), "ingen")
        return {"dagsform": form, "svar": SVAR_UTEN_AI[form]}

    import anthropic

    from .ai import STANDARD_MODELL

    svar = anthropic.Anthropic().messages.create(
        model=modell or os.getenv("MODELL", STANDARD_MODELL),
        max_tokens=300,
        system=CHAT_INSTRUKS,
        messages=[{"role": "user", "content": tekst}],
        output_config={"format": {"type": "json_schema", "schema": DAGSFORM_SKJEMA}},
    )
    return json.loads(next(b.text for b in svar.content if b.type == "text"))


def oppdater_bilde(bilde: dict, dagsform: str) -> dict:
    """Legger dagsformen inn i brukerbildet (innsjekk_i_dag og sykdom, se docs/avtale.md)."""
    b = copy.deepcopy(bilde)
    if dagsform == "ingen":
        return b
    i_dag = b["dato_i_dag"]
    innsjekk = dict(b.get("innsjekk_i_dag") or {"sovn": "ok"})
    sykdom = b.get("sykdom") or {}
    var_syk = innsjekk.get("folelse") == "syk" or (sykdom.get("syk_fra") and not sykdom.get("frisk_fra"))

    if dagsform == "syk":
        syk_fra = sykdom.get("syk_fra") if var_syk and sykdom.get("syk_fra") else i_dag
        b["sykdom"] = {"syk_fra": syk_fra, "frisk_fra": None}
    elif dagsform == "frisk":
        if not var_syk:
            dagsform = "ok"  # var ikke syk, så «frisk» betyr bare at alt er fint
        else:
            b["sykdom"] = {"syk_fra": sykdom.get("syk_fra") or i_dag, "frisk_fra": i_dag}
    innsjekk["folelse"] = dagsform
    b["innsjekk_i_dag"] = innsjekk
    return b
