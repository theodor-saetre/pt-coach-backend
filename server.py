"""
PT-coach API-server.

Start:
    uvicorn server:app --reload

Sider:
    GET  /               – utøvervelger (redirect til /u/<id>)
    GET  /u/<id>         – utøvervisning
    GET  /trener         – trenervisning

API:
    GET  /helse
    GET  /utovere                        – alle utøvere
    POST /utovere                        – opprett utøver
    GET  /utovere/<id>/plan              – planlagte økter
    POST /utovere/<id>/plan              – legg til planlagt økt
    DELETE /utovere/<id>/plan/<okt_id>   – slett planlagt økt
    GET  /utovere/<id>/logg              – utførte økter
    POST /utovere/<id>/logg              – logg utført økt (AI-parsing)
    GET  /utovere/<id>/meldinger         – chat
    POST /utovere/<id>/meldinger         – send melding
"""

from datetime import date
from pathlib import Path

from dotenv import load_dotenv

load_dotenv(Path(__file__).resolve().parent / ".env")

from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import HTMLResponse

from coach import lag_ukeplan
from coach.chat import tolk_melding, oppdater_bilde
from coach.dagbok import parse_okt, parse_okt_bare, les_okter
from coach.db import (
    init_db,
    hent_alle_utovere, opprett_utover, hent_utover,
    hent_plan, legg_til_planlagt, slett_planlagt,
    hent_logg, logg_utfort,
    hent_meldinger, send_melding,
)

init_db()

app = FastAPI(title="PT-coach", version="2.0")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)


# ── Statiske sider ────────────────────────────────────────────────────────────

def _les_html(filnavn: str) -> str:
    return (Path(__file__).parent / "frontend" / filnavn).read_text(encoding="utf-8")


@app.get("/", response_class=HTMLResponse)
def rot():
    return _les_html("velger.html")


@app.get("/u/{utover_id}", response_class=HTMLResponse)
def utover_side(utover_id: str):
    return _les_html("utover.html")


@app.get("/trener", response_class=HTMLResponse)
def trener_side():
    return _les_html("trener.html")


# ── Helse ─────────────────────────────────────────────────────────────────────

@app.get("/helse")
def helse():
    return {"status": "ok"}


# ── Utøvere ───────────────────────────────────────────────────────────────────

@app.get("/utovere")
def alle_utovere():
    return hent_alle_utovere()


@app.post("/utovere", status_code=201)
def ny_utover(data: dict):
    navn = (data.get("navn") or "").strip()
    if not navn:
        raise HTTPException(400, "Mangler 'navn'")
    return opprett_utover(navn)


@app.get("/utovere/{utover_id}")
def en_utover(utover_id: str):
    u = hent_utover(utover_id)
    if not u:
        raise HTTPException(404, "Utøver ikke funnet")
    return u


# ── Plan ──────────────────────────────────────────────────────────────────────

@app.get("/utovere/{utover_id}/plan")
def plan(utover_id: str):
    if not hent_utover(utover_id):
        raise HTTPException(404, "Utøver ikke funnet")
    return hent_plan(utover_id)


@app.post("/utovere/{utover_id}/plan", status_code=201)
def legg_til_plan(utover_id: str, data: dict):
    if not hent_utover(utover_id):
        raise HTTPException(404, "Utøver ikke funnet")
    for felt in ("dato", "type", "tittel"):
        if not data.get(felt):
            raise HTTPException(400, f"Mangler '{felt}'")
    return legg_til_planlagt(utover_id, data)


@app.delete("/utovere/{utover_id}/plan/{okt_id}")
def slett_plan(utover_id: str, okt_id: str):
    if not slett_planlagt(okt_id):
        raise HTTPException(404, "Økt ikke funnet")
    return {"slettet": True}


# ── Logg ──────────────────────────────────────────────────────────────────────

@app.get("/utovere/{utover_id}/logg")
def logg(utover_id: str):
    if not hent_utover(utover_id):
        raise HTTPException(404, "Utøver ikke funnet")
    return hent_logg(utover_id)


@app.post("/utovere/{utover_id}/logg", status_code=201)
def logg_okt(utover_id: str, data: dict):
    if not hent_utover(utover_id):
        raise HTTPException(404, "Utøver ikke funnet")
    tekst = (data.get("tekst") or "").strip()
    if not tekst:
        raise HTTPException(400, "Mangler 'tekst'")
    try:
        okt = parse_okt(tekst, dato=data.get("dato"))
    except Exception as e:
        raise HTTPException(500, str(e))
    return logg_utfort(utover_id, okt, planlagt_id=data.get("planlagt_id"))


@app.post("/utovere/{utover_id}/logg/parse")
def logg_parse(utover_id: str, data: dict):
    """Analyser tekst med AI og returner strukturert økt – uten å lagre."""
    if not hent_utover(utover_id):
        raise HTTPException(404, "Utøver ikke funnet")
    tekst = (data.get("tekst") or "").strip()
    if not tekst:
        raise HTTPException(400, "Mangler 'tekst'")
    try:
        return parse_okt_bare(tekst, dato=data.get("dato"))
    except Exception as e:
        raise HTTPException(500, str(e))


@app.post("/utovere/{utover_id}/logg/direkte", status_code=201)
def logg_direkte(utover_id: str, data: dict):
    """Logg ferdigstrukturerte øvelser uten AI-parsing (brukes for underveis-logging)."""
    if not hent_utover(utover_id):
        raise HTTPException(404, "Utøver ikke funnet")
    okt = {
        "type": data.get("type", "styrke"),
        "tittel": data.get("tittel", "Økt"),
        "minutter": data.get("minutter", 0),
        "km": 0,
        "intensitet": data.get("intensitet", "moderat"),
        "rpe": data.get("rpe", 0),
        "noter": data.get("noter", ""),
        "ovelser": data.get("ovelser", []),
        "dato": data.get("dato") or str(date.today()),
        "original_tekst": "",
    }
    return logg_utfort(utover_id, okt, planlagt_id=data.get("planlagt_id"))


# ── Meldinger ─────────────────────────────────────────────────────────────────

@app.get("/utovere/{utover_id}/meldinger")
def meldinger(utover_id: str, etter: str | None = None):
    if not hent_utover(utover_id):
        raise HTTPException(404, "Utøver ikke funnet")
    return hent_meldinger(utover_id, etter=etter)


@app.post("/utovere/{utover_id}/meldinger", status_code=201)
def ny_melding(utover_id: str, data: dict):
    if not hent_utover(utover_id):
        raise HTTPException(404, "Utøver ikke funnet")
    tekst = (data.get("tekst") or "").strip()
    fra = data.get("fra")
    if not tekst or fra not in ("trener", "utover"):
        raise HTTPException(400, "Mangler 'tekst' eller ugyldig 'fra'")
    return send_melding(utover_id, fra, tekst)


# ── Gammel dagbok-API (bakoverkompatibel) ─────────────────────────────────────

@app.post("/okter/logg")
def logg_okt_gammel(data: dict):
    tekst = (data.get("tekst") or "").strip()
    if not tekst:
        raise HTTPException(400, "Mangler 'tekst'")
    try:
        return parse_okt(tekst, dato=data.get("dato"))
    except Exception as e:
        raise HTTPException(500, str(e))


@app.get("/okter")
def hent_okter():
    return sorted(les_okter(), key=lambda o: o.get("dato", ""), reverse=True)


# ── Gammel plan-API ───────────────────────────────────────────────────────────

@app.post("/plan")
def lag_plan(bilde: dict):
    try:
        return lag_ukeplan(bilde)
    except Exception as e:
        raise HTTPException(500, str(e))


@app.post("/plan/uten-ai")
def lag_plan_uten_ai(bilde: dict):
    try:
        return lag_ukeplan(bilde, uten_ai=True)
    except Exception as e:
        raise HTTPException(500, str(e))


@app.post("/chat")
def chat(data: dict):
    tekst = data.get("tekst", "")
    bilde = data.get("bilde")
    if not tekst or bilde is None:
        raise HTTPException(400, "Mangler 'tekst' eller 'bilde'")
    tolket = tolk_melding(tekst)
    oppdatert = oppdater_bilde(bilde, tolket["dagsform"])
    return {**tolket, "bilde": oppdatert}


@app.post("/chat/prat")
def chat_prat(data: dict):
    """Generell AI-samtale med coachen. Kjenner brukerens profil og plan."""
    import anthropic, os, json as _json

    meldinger = data.get("meldinger", [])  # [{role, content}, ...]
    bilde = data.get("bilde") or {}

    if not meldinger:
        raise HTTPException(400, "Mangler 'meldinger'")

    bruker = bilde.get("bruker", {})
    mal = bruker.get("mal", "")
    niva = bruker.get("niva_egenvurdering", "")
    utstyr = ", ".join(bruker.get("utstyr") or [])
    dager = bruker.get("okter_per_uke", 4)
    min_per = bruker.get("minutter_per_okt", 60)
    navn = bruker.get("navn", "")

    system = (
        f"Du er en personlig PT-coach i en norsk treningsapp. "
        f"{'Brukerens navn er ' + navn + '.' if navn else ''} "
        f"Mål: {mal}. Nivå: {niva}. Utstyr: {utstyr}. "
        f"Trener {dager} dager/uke, {min_per} min per økt. "
        "Svar alltid kort (1–4 setninger), på norsk, som en PT ville gjort: konkret og motiverende. "
        "Ikke gi medisinske råd. Hvis brukeren melder at de er syk/sliten/pigg, noter det og juster forventningene."
    )

    try:
        klient = anthropic.Anthropic(api_key=os.getenv("ANTHROPIC_API_KEY"))
        svar = klient.messages.create(
            model=os.getenv("MODELL", "claude-haiku-5-5"),
            max_tokens=300,
            system=system,
            messages=meldinger,
        )
        tekst_svar = svar.content[0].text
    except Exception as e:
        raise HTTPException(500, str(e))

    # Sjekk dagsform i bakgrunnen
    try:
        tolket = tolk_melding(meldinger[-1]["content"])
        oppdatert_bilde = oppdater_bilde(bilde, tolket["dagsform"])
    except Exception:
        tolket = {"dagsform": "ingen"}
        oppdatert_bilde = bilde

    return {"svar": tekst_svar, "dagsform": tolket["dagsform"], "bilde": oppdatert_bilde}
