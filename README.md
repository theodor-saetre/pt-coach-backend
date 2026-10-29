# PT-coachen – AI-kjernen

Dette er hjernen i appen: den lager en ukeplan for trening og dagsmål for mat, ut fra hvem brukeren er og hva hen har gjort. Den kjører på PC-en din, uten app. Appen kobles på senere.

## Slik fungerer den

```
brukerbilde (JSON) ──► 1. REGLER ──► 2. CLAUDE ──► 3. KONTROLL ──► 4. MAT ──► ferdig plan
                         faste tall    lager planen   sjekker mot     dagsmål
                         og sperrer    som en PT      reglene         per dag
                                           ▲               │
                                           └── feil? prøv igjen (maks 3 ganger)
```

1. **Regler** (`coach/regler.py`) regner ut alt som skal være fast og trygt: energibehov og dagsmål for mat, største trygge underskudd, pulssoner, løpenivå ut fra tempo, belastning siste uke mot siste måned, og neste vekt i styrke.
2. **Claude** (`coach/ai.py` + `coach/instruks.md`) får tallene og lager uka, som en PT. Den må svare i et fast format (`coach/planformat.py`).
3. **Kontrollen** (`coach/sjekk.py`) sjekker planen: for mye trening, harde dager på rad, trening når du er syk, feil vekter, manglende varsler. Finner den feil, får Claude beskjed og lager planen på nytt.
4. **Mat**: koden regner ut kalorier, protein, karbohydrater og fett for hver dag, ut fra dagens økt. AI-en regner aldri ut mat selv.

Dette kalles en *arbeidsflyt*: koden styrer stegene, og AI-en gjør én jobb. Det er den tryggeste måten å starte på.

## Kom i gang på Windows

**1. Installer Python**
Last ned Python 3.12 eller nyere fra [python.org](https://www.python.org/downloads/). Huk av for **«Add python.exe to PATH»** i installasjonen.

**2. Installer VS Code** (anbefalt)
Last ned fra [code.visualstudio.com](https://code.visualstudio.com/) og legg til tillegget «Python» fra Microsoft.

**3. Åpne prosjektet**
Pakk ut zip-filen, for eksempel til `Dokumenter\pt-coach`. Åpne mappen i VS Code og velg **Terminal → New Terminal**.

**4. Sett opp et eget Python-miljø for prosjektet** (én gang)
```powershell
py -m venv .venv
.venv\Scripts\Activate.ps1
pip install -r requirements.txt
```
Får du feilmelding om at skript er blokkert, kjør denne én gang og prøv igjen:
```powershell
Set-ExecutionPolicy -Scope CurrentUser RemoteSigned
```
Du ser `(.venv)` foran linjen når miljøet er aktivt. Neste gang trenger du bare `.venv\Scripts\Activate.ps1`.

**5. Test uten AI (gratis)**
```powershell
python kjor_tester.py --uten-ai
```
Åpne `resultater/rapport.md` og trykk `Ctrl+Shift+V` i VS Code for å se den pent.

**6. Koble til Claude**
- Lag en konto på [console.anthropic.com](https://console.anthropic.com/), fyll på litt kreditt og lag en API-nøkkel.
- Kopier `.env.eksempel` til en ny fil som heter `.env`, og lim inn nøkkelen.
- Kjør:
```powershell
python lag_plan.py testbrukere/02_sterk_loper_8km_30min.json
python kjor_tester.py
```
Hver plan koster litt. Følg med på forbruket i konsollen.

## Filene

| Fil | Hva |
|---|---|
| `coach/regler.py` | Alle faste tall og sperrer. Endre regler her. |
| `coach/instruks.md` | Instruksen til PT-en. Her jobber du mest med tone og innhold. |
| `coach/planformat.py` | Formatet AI-en må svare i |
| `coach/sjekk.py` | Kontrollen, og utregning av mat per dag |
| `coach/ai.py` | Kobler alt sammen og kaller Claude |
| `coach/uten_ai.py` | Enkel reserveplan bare fra reglene (testmodus) |
| `testbrukere/` | 10 oppdiktede brukere som tester ulike situasjoner |
| `meg.json` | Mal for deg selv. Bytt ut tallene med dine egne. |
| `docs/avtale.md` | Formatet appen sender inn og får tilbake |
| `lag_plan.py` | Lag plan for én bruker |
| `kjor_tester.py` | Kjør alle testbrukerne og lag rapport |

## Det du kan jobbe med nå

1. **Les rapporten** fra `kjor_tester.py` og vurder hver plan som om du var PT: ville du gitt denne planen til denne personen?
2. **Endre instruksen** (`coach/instruks.md`) og kjør testene på nytt. Ble planene bedre?
3. **Legg til testbrukere** i `testbrukere/` for situasjoner du mener mangler, f.eks. en skadet bruker eller en som bare har 20 minutter.
4. **Bruk den på deg selv** i en uke: oppdater `meg.json` hver morgen med det du gjorde i går og hvordan du føler deg, og lag dagens plan.
5. **Juster en regel** i `coach/regler.py` hvis du er faglig uenig, for eksempel proteinmengde eller hvor mye treningen får øke per uke.

## Personvern

- Navn, e-post og telefon fjernes før noe sendes til Claude.
- Testbrukerne er oppdiktet. Før du bruker coachen med ekte testere, trenger du samtykke fra dem og en databehandleravtale med Anthropic. Sjekk også hvor lenge dataene lagres.
- `.env` med nøkkelen din skal aldri deles eller lastes opp.

## Neste steg

- **Coach-chat som agent:** La brukeren spørre PT-en fritt. Claude får reglene som verktøy den selv kan bruke, for eksempel `pulssoner()` eller `styrke_neste()`.
- **Matbilde:** Claude anslår innholdet fra et bilde, og brukeren bekrefter.
- **Server:** Legg coachen ut som en enkel nettjeneste (f.eks. med FastAPI) i EU, så appen kan kalle den.
