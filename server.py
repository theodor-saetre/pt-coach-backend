"""
PT-coach API-server.

Start:
    .venv\Scripts\Activate.ps1
    uvicorn server:app --reload

Endepunkter:
    GET  /helse          – sjekk at serveren kjører
    POST /plan           – lag ukeplan (brukerbilde som JSON-kropp)
    POST /plan/uten-ai   – lag ukeplan uten AI (gratis, til testing)
    POST /chat           – tolk dagsform-melding fra brukeren
"""

from dotenv import load_dotenv

load_dotenv()

from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware

from coach import lag_ukeplan
from coach.chat import tolk_melding, oppdater_bilde

app = FastAPI(title="PT-coach", version="1.0")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.get("/helse")
def helse():
    return {"status": "ok"}


@app.post("/plan")
def lag_plan(bilde: dict):
    try:
        return lag_ukeplan(bilde)
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/plan/uten-ai")
def lag_plan_uten_ai(bilde: dict):
    try:
        return lag_ukeplan(bilde, uten_ai=True)
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/chat")
def chat(data: dict):
    """
    Inn:  {"tekst": "jeg er syk i dag", "bilde": {...brukerbilde...}}
    Ut:   {"dagsform": "syk", "svar": "...", "bilde": {...oppdatert...}}
    """
    tekst = data.get("tekst", "")
    bilde = data.get("bilde")
    if not tekst or bilde is None:
        raise HTTPException(status_code=400, detail="Mangler 'tekst' eller 'bilde'")

    tolket = tolk_melding(tekst)
    oppdatert = oppdater_bilde(bilde, tolket["dagsform"])
    return {**tolket, "bilde": oppdatert}
