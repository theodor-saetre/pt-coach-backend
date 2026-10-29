"""
REGELMOTOREN – de faste, trygge tallene.

Her regner vi ut alt som skal være likt hver gang og aldri får bli farlig:
energibehov, dagsmål for mat, pulssoner, løpenivå, belastning og vekter i styrke.

AI-en får disse tallene servert og skal ikke finne på egne. Det er dette som gjør
coachen trygg: AI-en er PT-en som forklarer og setter sammen planen, men tallene
kommer herfra. Vil du endre en regel, gjør du det her, ikke i instruksen.
"""

from __future__ import annotations

from datetime import date, timedelta

# ---------------------------------------------------------------------------
# Sperrer. Endre bare hvis du har et faglig grunnlag for det.
# ---------------------------------------------------------------------------
MAKS_UNDERSKUDD_KCAL = 500        # aldri mer enn dette per dag (ca. 0,5 kg i uka)
MAKS_UNDERSKUDD_ANDEL = 0.20      # og aldri mer enn 20 % av dagsbehovet
OVERSKUDD_STYRKE_KCAL = 200       # lite overskudd ved mål om å bygge muskler
STOR_VEKTNEDGANG_KG = 20          # over dette: anbefal å snakke med fastlegen
BELASTNING_FORHOYET = 1.3        # forhold 7 dager mot snitt av 28 dager: ikke øk mer
BELASTNING_HOY = 1.5              # over dette: trapp ned (økt skaderisiko)
BELASTNING_LAV = 0.8
MAKS_OKNING_UKE = 1.10            # maks 10 % mer treningstid enn snittet

# Hvor anstrengende en økt er når brukeren ikke har oppgitt det (1–10)
STANDARD_RPE = {"lop": 5, "styrke": 6, "sykkel": 5, "padel": 6, "fotball": 7, "gange": 2, "annet": 5}

# Omtrentlig energiforbruk (MET) per økttype og intensitet
MET = {
    ("lop", "rolig"): 8.0, ("lop", "moderat"): 9.8, ("lop", "hard"): 11.5,
    ("styrke", "rolig"): 3.5, ("styrke", "moderat"): 5.0, ("styrke", "hard"): 6.0,
    ("sykkel", "rolig"): 6.0, ("sykkel", "moderat"): 8.0, ("sykkel", "hard"): 10.0,
    ("padel", "moderat"): 7.0, ("gange", "rolig"): 3.5, ("annet", "moderat"): 5.0,
}


# ---------------------------------------------------------------------------
# Hjelpefunksjoner
# ---------------------------------------------------------------------------
def _dato(s: str) -> date:
    return date.fromisoformat(s)


def _tempo_tekst(sek_per_km: float) -> str:
    m, s = divmod(int(round(sek_per_km)), 60)
    return f"{m}:{s:02d}/km"


def kcal_for_okt(type_: str, intensitet: str, minutter: float, vekt_kg: float) -> int:
    """Omtrentlig forbruk for én økt. Formel: MET × 3,5 × kg / 200 per minutt."""
    met = MET.get((type_, intensitet)) or MET.get((type_, "moderat")) or 5.0
    return round(met * 3.5 * vekt_kg / 200 * minutter)


# ---------------------------------------------------------------------------
# 1. Energi og dagsmål for mat
# ---------------------------------------------------------------------------
def energi_og_dagsmal(bruker: dict) -> dict:
    """
    Hvilemetabolisme med Mifflin-St Jeor, ganget med en faktor for vanlig hverdagsaktivitet.
    Treningen kommer i tillegg, og legges på dag for dag i planen.
    """
    vekt = float(bruker["vekt_kg"])
    hoyde = float(bruker["hoyde_cm"])
    alder = int(bruker.get("alder") or 30)
    kjonn = bruker.get("kjonn", "ukjent")
    justering = {"mann": 5, "kvinne": -161}.get(kjonn, -78)  # ukjent: snitt av de to

    bmr = 10 * vekt + 6.25 * hoyde - 5 * alder + justering
    hverdag = bmr * 1.4  # lett aktiv hverdag, uten trening

    mal = bruker.get("mal", "holde_formen")
    varsler: list[str] = []
    underskudd = 0
    malvekt = bruker.get("malvekt_kg")
    hoyde_m = hoyde / 100

    if malvekt:
        bmi_mal = malvekt / hoyde_m**2
        if bmi_mal < 18.5:
            varsler.append(
                "Målvekten er under normalvekt for høyden. Ikke lag vektnedgangsplan mot dette målet, "
                "og anbefal å snakke med fastlegen om hva som er riktig."
            )
            if mal == "ned_i_vekt":
                mal = "holde_formen"
        elif vekt - malvekt > STOR_VEKTNEDGANG_KG:
            varsler.append(
                f"Målet er å gå ned over {STOR_VEKTNEDGANG_KG} kg. Anbefal å snakke med fastlegen før start."
            )

    if mal == "ned_i_vekt":
        underskudd = round(min(MAKS_UNDERSKUDD_KCAL, hverdag * MAKS_UNDERSKUDD_ANDEL))
    kcal_hviledag = hverdag - underskudd
    if mal == "styrke":
        kcal_hviledag += OVERSKUDD_STYRKE_KCAL

    # Sperre: aldri under hvilemetabolismen
    if kcal_hviledag < bmr:
        kcal_hviledag = bmr
        underskudd = round(hverdag - bmr)

    # Protein: per kg, men regnet fra en vekt som tilsvarer KMI 25 ved høy kroppsvekt,
    # så tallet ikke blir urimelig høyt.
    vekt_for_protein = min(vekt, 25 * hoyde_m**2)
    g_per_kg = {"styrke": 1.8, "ned_i_vekt": 1.8}.get(mal, 1.4)
    protein = round(vekt_for_protein * g_per_kg)

    def makro(kcal: float) -> dict:
        fett = round(kcal * 0.30 / 9)
        karbo = round(max(0, kcal - protein * 4 - fett * 9) / 4)
        return {"kcal": round(kcal / 10) * 10, "protein_g": protein, "karbo_g": karbo, "fett_g": fett}

    return {
        "hvilemetabolisme_kcal": round(bmr),
        "hverdagsbehov_kcal": round(hverdag),
        "underskudd_kcal": underskudd,
        "mal_brukt": mal,
        "hviledag": makro(kcal_hviledag),
        "regel_treningsdag": "Legg kcal for dagens økt(er) til hviledagsmålet, som karbohydrater.",
        "forventet_vektendring_kg_per_uke": round(-underskudd * 7 / 7700, 2) if underskudd else 0.0,
        "varsler": varsler,
    }


# ---------------------------------------------------------------------------
# 2. Pulssoner (Karvonen: hvilepuls + prosent av pulsreserven)
# ---------------------------------------------------------------------------
def pulssoner(bruker: dict, puls: dict) -> dict:
    alder = int(bruker.get("alder") or 30)
    makspuls = puls.get("makspuls")
    kilde = "oppgitt"
    if not makspuls:
        makspuls = round(208 - 0.7 * alder)  # Tanaka-formelen, et estimat
        kilde = "estimert fra alder"
    hvile = puls.get("hvilepuls") or 60
    reserve = makspuls - hvile
    grenser = [(1, 0.50, 0.60, "veldig rolig"), (2, 0.60, 0.70, "rolig, kan prate"),
               (3, 0.70, 0.80, "moderat"), (4, 0.80, 0.90, "hardt, terskel"), (5, 0.90, 1.00, "maks")]
    soner = [
        {"sone": n, "fra": round(hvile + reserve * lo), "til": round(hvile + reserve * hi), "beskrivelse": b}
        for n, lo, hi, b in grenser
    ]
    return {"makspuls": makspuls, "makspuls_kilde": kilde, "hvilepuls": hvile, "soner": soner}


# ---------------------------------------------------------------------------
# 3. Løpenivå fra tempo (8 km på 30 min og på 60 min gir helt ulike planer)
# ---------------------------------------------------------------------------
def lopeniva(okter: list[dict], bruker: dict, i_dag: date) -> dict:
    lop = [o for o in okter if o.get("type") == "lop" and o.get("km") and o.get("minutter") and o["km"] >= 3]
    if not lop:
        egen = bruker.get("niva_egenvurdering", "nybegynner")
        return {
            "har_data": False,
            "niva": egen,
            "forklaring": "Ingen løpeturer med distanse ennå. Bruk brukerens egen vurdering og styr på følelse "
                          "(rolig = kan prate). Be om én registrert tur for å finne nivået.",
        }

    # Raskeste tur er det beste anslaget på kapasitet. Omregnet til 10 km med Riegels formel.
    def tid_10k(o: dict) -> float:
        return o["minutter"] * 60 * (10 / o["km"]) ** 1.06

    beste = min(lop, key=tid_10k)
    t10 = tid_10k(beste)
    tempo_10k = t10 / 10  # sekunder per km
    minutter_10k = t10 / 60
    if minutter_10k < 40:
        niva = "sterk"
    elif minutter_10k < 50:
        niva = "godt trent"
    elif minutter_10k < 62:
        niva = "mosjonist"
    else:
        niva = "nybegynner"

    siste_4u = [o for o in lop if 0 <= (i_dag - _dato(o["dato"])).days < 28]
    km_uke = round(sum(o["km"] for o in siste_4u) / 4, 1)
    return {
        "har_data": True,
        "niva": niva,
        "beste_tur": f'{beste["km"]} km på {beste["minutter"]} min ({_tempo_tekst(beste["minutter"] * 60 / beste["km"])})',
        "beregnet_10km_min": round(minutter_10k),
        "rolig_tempo": f"{_tempo_tekst(tempo_10k * 1.20)}–{_tempo_tekst(tempo_10k * 1.32)}",
        "terskel_tempo": _tempo_tekst(tempo_10k * 1.04),
        "intervall_tempo": _tempo_tekst(tempo_10k * 0.97),
        "snitt_km_per_uke_siste_4_uker": km_uke,
        "gaa_jogg_anbefales": minutter_10k > 75,
    }


# ---------------------------------------------------------------------------
# 4. Belastning: siste 7 dager mot snittet av siste 28 dager
# ---------------------------------------------------------------------------
def belastning(okter: list[dict], i_dag: date, bruker: dict) -> dict:
    def last(o: dict) -> float:
        rpe = o.get("rpe") or STANDARD_RPE.get(o.get("type", "annet"), 5)
        return o["minutter"] * rpe

    def innen(dager: int) -> list[dict]:
        return [o for o in okter if 0 <= (i_dag - _dato(o["dato"])).days < dager]

    # Del bare på ukene vi faktisk har data for (maks 4), ellers ser nye brukere overbelastet ut
    siste_28 = innen(28)
    if siste_28:
        dager_med_historikk = (i_dag - min(_dato(o["dato"]) for o in siste_28)).days + 1
    else:
        dager_med_historikk = 0
    uker = min(4.0, max(1.0, dager_med_historikk / 7))

    akutt = sum(last(o) for o in innen(7))
    kronisk = sum(last(o) for o in siste_28) / uker
    min_uke_snitt = sum(o["minutter"] for o in siste_28) / uker
    ratio = round(akutt / kronisk, 2) if kronisk else None

    if ratio is None or dager_med_historikk < 14:
        status = "ny"  # for lite historikk til å vurdere belastning: start forsiktig
    elif ratio > BELASTNING_HOY:
        status = "hoy"
    elif ratio > BELASTNING_FORHOYET:
        status = "forhoyet"
    elif ratio < BELASTNING_LAV:
        status = "lav"
    else:
        status = "trygg"

    egen = bruker.get("niva_egenvurdering", "nybegynner")
    gulv = {"nybegynner": 90, "middels": 150, "erfaren": 210}.get(egen, 90)  # trygt minimum per uke
    tilgjengelig = int(bruker.get("okter_per_uke", 3)) * int(bruker.get("minutter_per_okt", 45))
    if status == "hoy":
        maks_min = round(min_uke_snitt * 0.9)                      # trapp ned 10 %
    elif status == "forhoyet":
        maks_min = max(gulv, round(min_uke_snitt))                 # hold nivået, ingen økning
    else:
        maks_min = max(gulv, round(min_uke_snitt * MAKS_OKNING_UKE))
    maks_min = min(tilgjengelig, maks_min)

    maks_harde = {"nybegynner": 1, "middels": 2, "erfaren": 2}.get(egen, 1)
    if status == "hoy":
        maks_harde = 0
    elif status in ("forhoyet", "ny"):
        maks_harde = min(maks_harde, 1)

    return {
        "akutt_7d": round(akutt), "kronisk_snitt_28d": round(kronisk), "forhold": ratio, "status": status,
        "snitt_minutter_per_uke": round(min_uke_snitt),
        "maks_minutter_neste_7_dager": maks_min,
        "maks_harde_okter_neste_7_dager": maks_harde,
        "maks_okter_neste_7_dager": int(bruker.get("okter_per_uke", 3)),
    }


# ---------------------------------------------------------------------------
# 5. Styrke: dobbel progresjon (8–10 reps; alle sett på 10 → mer vekt)
# ---------------------------------------------------------------------------
def styrke_neste(styrke_logg: list[dict]) -> list[dict]:
    siste: dict[str, dict] = {}
    for rad in sorted(styrke_logg, key=lambda r: r["dato"]):
        siste[rad["ovelse"]] = rad

    forslag = []
    for navn, rad in siste.items():
        lo, hi = rad.get("rep_fra", 8), rad.get("rep_til", 10)
        steg = rad.get("steg_kg") or (2.0 if "manual" in navn.lower() else 2.5)
        kg, reps = float(rad["kg"]), list(rad["reps"])
        if reps and all(r >= hi for r in reps):
            ny_kg, mal_reps, hvorfor = kg + steg, lo, f"alle sett nådde {hi} reps → +{steg:g} kg"
        elif sum(1 for r in reps if r < lo) >= 2:
            ny_kg, mal_reps, hvorfor = max(steg, kg - steg), hi, f"flere sett under {lo} reps → litt lettere"
        else:
            ny_kg, mal_reps, hvorfor = kg, hi, f"samme vekt, mål {hi} reps i alle sett"
        forslag.append({
            "ovelse": navn, "sist": f"{kg:g} kg × {', '.join(map(str, reps))}",
            "neste_kg": ny_kg, "sett": len(reps) or 3, "reps": f"{lo}-{hi}", "start_reps": mal_reps, "hvorfor": hvorfor,
        })
    return forslag


# ---------------------------------------------------------------------------
# 6. Dagens innsjekk
# ---------------------------------------------------------------------------
def dagens_justering(innsjekk: dict | None) -> dict:
    if not innsjekk:
        return {"regel": "ingen innsjekk", "tillatt_i_dag": "som planlagt"}
    folelse = innsjekk.get("folelse")
    sovn = innsjekk.get("sovn")
    if folelse == "syk":
        return {"regel": "syk", "tillatt_i_dag": "hvile",
                "melding": "Ingen trening i dag. Aldri tren med feber. Kontakt lege ved vedvarende sykdom."}
    if folelse == "sliten" or sovn == "darlig":
        return {"regel": "sliten eller dårlig søvn", "tillatt_i_dag": "bare rolig og kortere (maks 75 % av planlagt tid)"}
    return {"regel": "i form", "tillatt_i_dag": "som planlagt"}


SKANSOM_KMI = 35  # fra denne KMI-en: start med gange, sykkel og styrke i stedet for løping


def _lop_med_sperrer(lop: dict, bruker: dict) -> dict:
    """Legger til hva slags løping som er trygt å planlegge."""
    kmi = float(bruker["vekt_kg"]) / (float(bruker["hoyde_cm"]) / 100) ** 2
    skansom = kmi >= SKANSOM_KMI
    lop["skansom_start"] = skansom
    lop["lop_tillatt"] = not skansom
    lop["harde_lopeokter_tillatt"] = (not skansom) and lop.get("har_data", False) and not lop.get("gaa_jogg_anbefales", False)
    if skansom:
        lop["skansom_forklaring"] = ("Start med gange, sykkel og styrke. Det er skånsomt for knær og ledd. "
                                     "Løping kan komme gradvis senere.")
    return lop


# ---------------------------------------------------------------------------
# Samle alt
# ---------------------------------------------------------------------------
UKEDAGER = ["mandag", "tirsdag", "onsdag", "torsdag", "fredag", "lørdag", "søndag"]


def beregn_fakta(bilde: dict) -> dict:
    """Tar inn brukerbildet (se docs/avtale.md) og returnerer alle faste tall."""
    i_dag = _dato(bilde["dato_i_dag"])
    bruker = bilde["bruker"]
    okter = sorted(bilde.get("okter_siste_6_uker", []), key=lambda o: o["dato"])

    dager = [{"dato": (i_dag + timedelta(days=i)).isoformat(),
              "dag": UKEDAGER[(i_dag + timedelta(days=i)).weekday()]} for i in range(7)]

    return {
        "dager_i_planen": dager,
        "bruk": bruker.get("bruk", {"plan": True, "trening": True, "kosthold": True, "tall": "standard"}),
        "energi": energi_og_dagsmal(bruker),
        "puls": pulssoner(bruker, bilde.get("puls", {})),
        "lop": _lop_med_sperrer(lopeniva(okter, bruker, i_dag), bruker),
        "belastning": belastning(okter, i_dag, bruker),
        "styrke": styrke_neste(bilde.get("styrke_logg", [])),
        "i_dag": dagens_justering(bilde.get("innsjekk_i_dag")),
        "vekt_kg": bruker["vekt_kg"],
    }
