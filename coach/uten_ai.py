"""
TESTMODUS – lager en enkel plan bare fra reglene, uten å kalle AI-en.

Brukes når du kjører med --uten-ai. Da kan du teste hele løypa (regler → plan →
kontroll → mat) gratis og uten API-nøkkel. Planen er bevisst enkel: det er AI-en
som skal gjøre den personlig.
"""

from __future__ import annotations

STANDARD_STYRKE = [
    ("Knebøy", "Hoftene bakover, knærne over tærne."),
    ("Push-ups", "Rett linje fra hode til hæl."),
    ("Roing med strikk eller manual", "Trekk albuene bakover, stram mage."),
    ("Utfall", "Langt steg, bakre kne nesten i gulvet."),
    ("Planke", "Hold 30–45 sekunder, ikke la hoftene synke."),
]


def lag_plan_uten_ai(fakta: dict, bruker: dict) -> dict:
    b = fakta["belastning"]
    mal = fakta["energi"]["mal_brukt"]
    # Færre økter heller enn for korte økter: minst 20 min per økt (eller det brukeren pleier), innenfor maks totaltid
    min_okt = max(20, b.get("min_lengste_kondisjonsokt_min") or 0)
    antall = min(b["maks_okter_neste_7_dager"], max(1, b["maks_minutter_neste_7_dager"] // min_okt))
    per_okt = max(min_okt, min(int(bruker.get("minutter_per_okt", 45)), b["maks_minutter_neste_7_dager"] // antall))
    if b.get("maks_minutter_per_okt"):
        per_okt = min(per_okt, b["maks_minutter_per_okt"])
    harde_igjen = b["maks_harde_okter_neste_7_dager"]

    # Fordel øktene jevnt over dagene etter eventuelle sykedager
    start = fakta["i_dag"].get("hviledager_forst", 0)
    plassering = {start + round(i * (7 - start) / antall) for i in range(antall)} if antall else set()
    typer = {
        "utholdenhet": ["lop", "lop", "styrke", "lop", "lop", "lop"],
        "styrke": ["styrke", "lop", "styrke", "styrke", "lop"],
        "ned_i_vekt": ["styrke", "gange", "lop", "styrke", "gange"],
    }.get(mal, ["lop", "styrke", "lop", "styrke", "lop"])

    lop = fakta["lop"]
    if not lop.get("lop_tillatt", True):
        typer = ["gange" if t == "lop" else t for t in typer]
    soner = {s["sone"]: s for s in fakta["puls"]["soner"]}
    dager, n, forrige_hard = [], 0, False
    for i, dag in enumerate(fakta["dager_i_planen"]):
        regel = fakta["i_dag"]["tillatt_i_dag"] if i == 0 else "hvile" if i < start else "som planlagt"
        if i not in plassering or regel == "hvile":
            dager.append(_hvile(dag, "Sykedag" if regel == "hvile" else "Hviledag"))
            forrige_hard = False
            continue
        typ = typer[n % len(typer)]
        n += 1
        minutter = round(per_okt * 0.75) if "kortere" in regel else per_okt
        hard = (typ == "lop" and lop.get("harde_lopeokter_tillatt", True) and harde_igjen > 0
                and not forrige_hard and regel == "som planlagt" and i > 0)
        if hard:
            harde_igjen -= 1
        forrige_hard = hard

        if typ == "styrke":
            dager.append(_styrke(dag, minutter, fakta))
        else:
            sone = soner[4] if hard else soner[2]
            dager.append({
                **dag, "type": typ,
                "tittel": "Intervaller" if hard else ("Gåtur" if typ == "gange" else "Rolig løp"),
                "minutter": minutter, "intensitet": "hard" if hard else "rolig",
                "pulssone": "4" if hard else "1-2" if typ == "gange" else "2",
                "tempo": (lop.get("intervall_tempo") if hard else lop.get("rolig_tempo", "")) or "",
                "beskrivelse": (f"Puls {sone['fra']}–{sone['til']}. "
                                + ("Dragene skal kjennes hardt, men kontrollert." if hard else "Du skal kunne prate hele veien.")),
                "deler": _intervalldeler(minutter) if hard else [{"tekst": "Rolig og jevnt", "minutter": minutter, "ganger": 1}],
                "ovelser": [],
            })

    varsler = list(fakta["energi"]["varsler"])
    if fakta["i_dag"].get("melding"):
        varsler.append(fakta["i_dag"]["melding"])
    return {
        "pt_melding": "TESTMODUS: Planen er laget av reglene alene, uten AI. Kjør uten --uten-ai for en personlig plan.",
        "dager": dager,
        "hvorfor": [
            f"Du har trent ca. {b['snitt_minutter_per_uke']} min i uka, og denne uka er på høyst {b['maks_minutter_neste_7_dager']} min.",
            f"Løpenivå: {lop.get('niva')}.",
        ],
        "trygghet": " ".join(varsler),
    }


def _hvile(dag: dict, tittel: str) -> dict:
    return {**dag, "type": "hvile", "tittel": tittel, "minutter": 0, "intensitet": "hvile",
            "pulssone": "", "tempo": "", "beskrivelse": "Hvile er en del av treningen.", "deler": [], "ovelser": []}


def _intervalldeler(minutter: int) -> list[dict]:
    """10 min oppvarming, drag på 3 min + 2 min rolig, og resten nedjogg. Summen blir alltid lik minutter."""
    drag = max(1, min(6, (minutter - 15) // 5))
    return [{"tekst": "Rolig oppvarming", "minutter": 10, "ganger": 1},
            {"tekst": "3 min drag + 2 min rolig jogg", "minutter": 5, "ganger": drag},
            {"tekst": "Rolig nedjogg", "minutter": minutter - 10 - 5 * drag, "ganger": 1}]


def _styrke(dag: dict, minutter: int, fakta: dict) -> dict:
    if fakta["styrke"]:
        ovelser = [{"navn": f["ovelse"], "sett": f["sett"], "reps": f["reps"], "kg": f["neste_kg"],
                    "tips": f"Sist {f['sist']}: {f['hvorfor']}."} for f in fakta["styrke"]]
    else:
        ovelser = [{"navn": n, "sett": 3, "reps": "8-10", "kg": 0, "tips": t} for n, t in STANDARD_STYRKE]
    return {**dag, "type": "styrke", "tittel": "Styrke", "minutter": minutter, "intensitet": "moderat",
            "pulssone": "", "tempo": "", "beskrivelse": "3 sett per øvelse, 1–2 min pause mellom settene.",
            "deler": [{"tekst": "Oppvarming", "minutter": 5, "ganger": 1},
                      {"tekst": "Øvelsene", "minutter": minutter - 10, "ganger": 1},
                      {"tekst": "Rolig avslutning", "minutter": 5, "ganger": 1}],
            "ovelser": ovelser}
