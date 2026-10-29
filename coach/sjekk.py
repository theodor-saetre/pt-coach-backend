"""
KONTROLLEN – sjekker AI-ens plan mot reglene før brukeren ser den.

Finner den feil, sendes feilene tilbake til AI-en, som får lage planen på nytt.
Etter at planen er godkjent, legger koden på dagsmålene for mat.
"""

from __future__ import annotations

import re

from .regler import kcal_for_okt

SLINGRINGSMONN = 1.05  # 5 % margin på totaltid
KONDISJON = ("lop", "gange", "sykkel")
MINUTTALL = re.compile(r"\d+\s*(min|minutt)", re.IGNORECASE)
# Ord fra regelmotoren som ikke skal vises til brukeren (se «Tone» i instruks.md)
MASKINORD = re.compile(r"\b(belastningspoeng|akutt|kronisk|status|forhoyet|hoy|regelmotor\w*|fakta|kg 0)\b", re.IGNORECASE)


def _okter(plan: dict) -> list[dict]:
    return [d for d in plan["dager"] if d["type"] != "hvile" and d["minutter"] > 0]


def sjekk_plan(plan: dict, fakta: dict) -> list[str]:
    feil: list[str] = []
    dager = plan.get("dager", [])
    forventet = fakta["dager_i_planen"]

    # 1. Riktige dager
    if len(dager) != 7:
        feil.append(f"Planen må ha nøyaktig 7 dager, men har {len(dager)}.")
    else:
        for d, f in zip(dager, forventet):
            if d["dato"] != f["dato"]:
                feil.append(f"Dag {d.get('dag')}: dato skal være {f['dato']}, ikke {d['dato']}.")

    b = fakta["belastning"]
    okter = _okter(plan)

    # 2. Ikke for mye trening
    total = sum(d["minutter"] for d in okter)
    if total > b["maks_minutter_neste_7_dager"] * SLINGRINGSMONN:
        feil.append(f"Total treningstid er {total} min, men maks er {b['maks_minutter_neste_7_dager']} min.")
    if len(okter) > b["maks_okter_neste_7_dager"]:
        feil.append(f"Planen har {len(okter)} økter, men brukeren har bare tid til {b['maks_okter_neste_7_dager']}.")
    harde = [d for d in okter if d["intensitet"] == "hard"]
    if len(harde) > b["maks_harde_okter_neste_7_dager"]:
        feil.append(f"Planen har {len(harde)} harde økter, men maks er {b['maks_harde_okter_neste_7_dager']}.")

    maks_per_okt = b.get("maks_minutter_per_okt")
    if maks_per_okt:
        for d in okter:
            if d["minutter"] > maks_per_okt:
                feil.append(f"{d['dag']}: økta er {d['minutter']} min, men etter sykdom er maks {maks_per_okt} min per økt.")

    # 2b. Ikke gå bakover: lengste kondisjonsøkt minst like lang som det brukeren pleier
    min_lengste = b.get("min_lengste_kondisjonsokt_min")
    kondisjon = [d for d in okter if d["type"] in KONDISJON]
    if min_lengste and kondisjon and max(d["minutter"] for d in kondisjon) < min_lengste:
        feil.append(f"Lengste kondisjonsøkt er {max(d['minutter'] for d in kondisjon)} min, men brukeren pleier "
                    f"{b['vanlig_kondisjonsokt_min']} min. Minst én kondisjonsøkt må være {min_lengste} min eller mer.")

    # 3. To harde dager på rad
    for a, c in zip(dager, dager[1:]):
        if a["intensitet"] == "hard" and c["intensitet"] == "hard":
            feil.append(f"Harde økter to dager på rad ({a['dag']} og {c['dag']}).")

    # 4. Dagens innsjekk og sykdom
    if dager:
        i_dag = dager[0]
        regel = fakta["i_dag"]["tillatt_i_dag"]
        if regel == "hvile" and i_dag["type"] != "hvile":
            feil.append("Brukeren er syk i dag. Dag 1 må være hvile.")
        if regel.startswith("bare rolig") and i_dag["intensitet"] not in ("hvile", "rolig"):
            feil.append("Dag 1 må være hvile eller rolig (sliten eller første dag etter sykdom).")
        for d in dager[1:fakta["i_dag"].get("hviledager_forst", 0)]:
            if d["type"] != "hvile":
                feil.append(f"{d['dag']}: brukeren er syk, så denne dagen må også være hvile.")

    # 4b. Regnestykket i økta må stemme, og minuttene står i deler, ikke i beskrivelsen
    for d in okter:
        deler = d.get("deler") or []
        if not deler:
            feil.append(f"{d['dag']}: økta mangler deler (f.eks. oppvarming, hoveddel, nedtrapping).")
            continue
        sum_min = sum(x["minutter"] * x["ganger"] for x in deler)
        if sum_min != d["minutter"]:
            regnestykke = " + ".join(f"{x['ganger']}×{x['minutter']}" if x["ganger"] > 1 else str(x["minutter"]) for x in deler)
            feil.append(f"{d['dag']}: delene blir {regnestykke} = {sum_min} min, men økta er {d['minutter']} min.")
        if d["type"] in KONDISJON and MINUTTALL.search(d["beskrivelse"]):
            feil.append(f"{d['dag']}: ikke skriv minuttall i beskrivelsen, de skal bare stå i deler.")

    # 5. Pulssone må passe intensiteten
    for d in okter:
        sone = d.get("pulssone", "")
        if d["type"] in ("lop", "sykkel") and sone:
            forste = sone.strip()[0]
            if d["intensitet"] == "rolig" and forste not in "12":
                feil.append(f"{d['dag']}: rolig økt skal være sone 1–2, ikke {sone}.")
            if d["intensitet"] == "hard" and forste not in "345":
                feil.append(f"{d['dag']}: hard økt skal være sone 4–5, ikke {sone}.")

    # 5b. Trygg løping
    lop = fakta["lop"]
    for d in okter:
        if d["type"] == "lop" and not lop.get("lop_tillatt", True):
            feil.append(f"{d['dag']}: ingen løping ennå (skånsom start). Bruk gange, sykkel eller styrke.")
        if d["type"] == "lop" and d["intensitet"] == "hard" and not lop.get("harde_lopeokter_tillatt", True):
            feil.append(f"{d['dag']}: harde løpeøkter er ikke tillatt for denne brukeren ennå.")
        tekst = " ".join([d["tittel"], d["beskrivelse"]] + [x["tekst"] for x in d.get("deler", [])]).lower()
        if d["type"] == "lop" and not lop.get("gaa_jogg_anbefales") and ("gå-jogg" in tekst or "gåjogg" in tekst):
            feil.append(f"{d['dag']}: brukeren har løpt {lop.get('lengste_lop_min')} min sammenhengende. "
                        "Gå-jogg er et steg tilbake; lag et sammenhengende rolig løp.")

    # 6. Styrkevekter må følge regelmotoren
    forslag = {f["ovelse"].lower(): f for f in fakta["styrke"]}
    for d in dager:
        for o in d.get("ovelser", []):
            f = forslag.get(o["navn"].lower())
            if f and abs(float(o["kg"]) - float(f["neste_kg"])) > 0.01:
                feil.append(f"{d['dag']}: {o['navn']} skal være {f['neste_kg']:g} kg ({f['hvorfor']}), ikke {o['kg']:g} kg.")

    # 7. Varsler må nå frem til brukeren
    maa_med = list(fakta["energi"]["varsler"])
    if fakta["i_dag"].get("melding"):
        maa_med.append(fakta["i_dag"]["melding"])
    if maa_med and not plan.get("trygghet", "").strip():
        feil.append("Feltet 'trygghet' er tomt, men disse varslene må med: " + " | ".join(maa_med))
    if any("fastlege" in v for v in maa_med) and "fastlege" not in plan.get("trygghet", "").lower():
        feil.append("Feltet 'trygghet' må anbefale brukeren å snakke med fastlegen.")

    # 7b. Ingen ord fra regelmotoren i teksten brukeren leser
    brukertekst = " ".join([plan.get("pt_melding", ""), plan.get("trygghet", "")] + plan.get("hvorfor", []))
    funnet = sorted({m.group(0).lower() for m in MASKINORD.finditer(brukertekst)})
    if funnet:
        feil.append(f"Ikke bruk ord fra regelmotoren ({', '.join(funnet)}). Si det som en PT, f.eks. «du har trent mer enn vanlig».")

    # 8. Stort vektmål: brukeren skal få et konkret delmål
    vektmal = fakta["energi"].get("vektmal")
    if vektmal and vektmal["stort_mal"]:
        alt = " ".join([plan.get("pt_melding", ""), plan.get("trygghet", "")] + plan.get("hvorfor", []))
        if str(vektmal["delmal_kg"]) not in alt:
            feil.append(f"Nevn første delmål på {vektmal['delmal_kg']} kg (ca. {vektmal['uker_til_delmal']} uker).")

    return feil


def legg_til_kosthold(plan: dict, fakta: dict) -> dict:
    """Regner ut dagsmål for mat for hver dag: hviledagsmål + forbruk på dagens økt."""
    if not fakta["bruk"].get("kosthold", True):
        return plan
    basis = fakta["energi"]["hviledag"]
    vekt = float(fakta["vekt_kg"])
    for d in plan["dager"]:
        okt_kcal = 0 if d["type"] == "hvile" else kcal_for_okt(d["type"], d["intensitet"], d["minutter"], vekt)
        kcal = round((basis["kcal"] + okt_kcal) / 10) * 10
        d["kosthold"] = {
            "kcal": kcal,
            "protein_g": basis["protein_g"],
            "karbo_g": basis["karbo_g"] + round(okt_kcal / 4),  # treningen dekkes med karbohydrater
            "fett_g": basis["fett_g"],
            "herav_trening_kcal": okt_kcal,
        }
    return plan
