"""Skriver en plan pent ut i terminalen og som Markdown til rapporten."""

from __future__ import annotations


def plan_som_tekst(resultat: dict, tittel: str = "") -> str:
    plan, fakta = resultat["plan"], resultat["fakta"]
    e, lop, b = fakta["energi"], fakta["lop"], fakta["belastning"]
    linjer = []
    if tittel:
        linjer += [f"## {tittel}", ""]

    status = "GODKJENT" if resultat["godkjent"] else "IKKE GODKJENT"
    linjer += [f"**{status}** · {resultat['modell']} · forsøk: {resultat['forsok']}", ""]

    linjer += [
        "**Fakta fra reglene**",
        f"- Løpenivå: {lop.get('niva')}" + (f" (beste tur {lop['beste_tur']}, rolig tempo {lop['rolig_tempo']})" if lop.get("har_data") else ""),
        f"- Belastning: {b['status']} (forhold {b['forhold']}), maks {b['maks_minutter_neste_7_dager']} min, "
        f"{b['maks_okter_neste_7_dager']} økter, {b['maks_harde_okter_neste_7_dager']} harde",
        f"- Mat hviledag: {e['hviledag']['kcal']} kcal · {e['hviledag']['protein_g']} g protein"
        + (f" · underskudd {e['underskudd_kcal']} kcal (ca. {abs(e['forventet_vektendring_kg_per_uke'])} kg/uke)" if e["underskudd_kcal"] else ""),
        *([f"- Vektmål: ned {e['vektmal']['ned_kg']:g} kg ({e['vektmal']['andel_prosent']} %), delmål {e['vektmal']['delmal_kg']} kg "
           f"om ca. {e['vektmal']['uker_til_delmal']} uker, mål om ca. {e['vektmal']['uker_til_malvekt']} uker"] if e.get("vektmal") else []),
        f"- I dag: {fakta['i_dag']['tillatt_i_dag']}" + (f" · sykdom: {fakta['sykdom']}" if fakta.get("sykdom") else ""),
        "",
        f"**PT:** {plan['pt_melding']}",
        "",
        "| Dag | Økt | Min | Intensitet | Sone/tempo | Mat (kcal · protein) |",
        "|---|---|---|---|---|---|",
    ]
    for d in plan["dager"]:
        mat = d.get("kosthold")
        mat_txt = f"{mat['kcal']} · {mat['protein_g']} g" if mat else "–"
        sone = " ".join(x for x in [f"sone {d['pulssone']}" if d["pulssone"] else "", d["tempo"]] if x) or "–"
        linjer.append(f"| {d['dag']} {d['dato'][5:]} | {d['tittel']} | {d['minutter']} | {d['intensitet']} | {sone} | {mat_txt} |")
        if d["beskrivelse"] and d["type"] != "hvile":
            linjer.append(f"|  | _{d['beskrivelse']}_ |  |  |  |  |")
        if d.get("deler") and d["type"] != "hvile":
            deler = " + ".join(f"{x['ganger']} × {x['minutter']} min {x['tekst']}" if x["ganger"] > 1
                               else f"{x['minutter']} min {x['tekst']}" for x in d["deler"])
            sum_min = sum(x["minutter"] * x["ganger"] for x in d["deler"])
            linjer.append(f"|  | {deler} = {sum_min} min |  |  |  |  |")
        for o in d.get("ovelser", []):
            kg = f"{o['kg']:g} kg" if o["kg"] else "velg vekt selv"
            linjer.append(f"|  | · {o['navn']}: {o['sett']} × {o['reps']}, {kg} |  |  |  |  |")
    linjer.append("")
    if plan.get("hvorfor"):
        linjer += ["**Hvorfor**"] + [f"- {h}" for h in plan["hvorfor"]] + [""]
    if plan.get("trygghet"):
        linjer += [f"**Trygghet:** {plan['trygghet']}", ""]
    if resultat["feil_underveis"]:
        linjer.append("**Feil som kontrollen fant underveis**")
        for i, feil in enumerate(resultat["feil_underveis"], 1):
            linjer += [f"- Forsøk {i}: " + "; ".join(feil)]
        linjer.append("")
    return "\n".join(linjer)
