# PT-coachen

AI-kjernen i en treningsapp for vanlige mosjonister i Norge. Målet: en lavterskel PT i lomma. Coachen lager ukeplan for trening og dagsmål for mat (kcal, protein, karbo, fett – ingen matretter), og tilpasser seg det brukeren faktisk gjør.

Les `docs/beslutninger.md` for bakgrunn, produktvalg og neste steg før du foreslår større endringer.

## Om meg (Theodor)
- Jeg lærer å kode. Forklar endringer kort på norsk, og vis hva du endret.
- Windows, PowerShell, VS Code, Python 3.13.
- Prosjektet ligger i `...\Skrivebord\pt-coach\pt-coach`. Python-miljøet ligger én mappe opp: aktiver med `..\.venv\Scripts\Activate.ps1`.
- Bruk Git: lagre en versjon (`git add .` + `git commit`) etter hver endring som fungerer.

## Arkitektur (arbeidsflyt, ikke fri agent)
1. `coach/regler.py` – faste tall og sperrer. All tallmagi skjer her, aldri i AI-en.
2. `coach/instruks.md` – systeminstruks til Claude (PT-tone og regler).
3. `coach/planformat.py` – JSON-skjema planen må følge (structured outputs via `output_config`).
4. `coach/sjekk.py` – kontrollerer planen mot reglene og legger på mat per dag.
5. `coach/ai.py` – regler → Claude → kontroll → nytt forsøk med feilene (maks 3).
- `coach/uten_ai.py` – reserveplan bare fra regler (`--uten-ai`).
- `coach/chat.py` – første versjon av chatten: forstår dagsform (syk, frisk, sliten, pigg) og oppdaterer brukerbildet.
- `docs/avtale.md` – formatet inn/ut mot den kommende appen. Ikke bryt det uten å oppdatere filen.

## Kommandoer
- `python kjor_tester.py --uten-ai` – gratis test av regler og kontroll (skal gi alle godkjent).
- `python chat.py testbrukere/<fil>.json [--uten-ai] [--melding "jeg er frisk"]` – chat med coachen.
- `python kjor_tester.py` – alle testbrukere med Claude. Rapport i `resultater/rapport.md`.
- `python lag_plan.py testbrukere/<fil>.json` – én bruker.

## Faste prinsipper
- Trygghet først: maks 500 kcal underskudd og aldri under hvilemetabolismen, skånsom start (ingen løping) ved KMI ≥ 35, ingen harde løpeøkter uten løpehistorikk, hvile ved sykdom og rolig opptrapping etterpå, aldri harde dager på rad, maks 10 % økning per uke.
- Vektmål regnes i prosent av kroppsvekten: over 10 % (eller KMI ≥ 35) gir anbefaling om fastlege og et første delmål på 5 %.
- Ikke gå bakover: ingen gå-jogg for den som løper sammenhengende, og lengste kondisjonsøkt minst 90 % av det brukeren pleier.
- Ingen medisinske råd. Ved sykdom, smerter eller store vektmål: anbefal fastlege.
- Faglig grunnlag: Helsedirektoratet, NNR 2023, ACSM.
- Personvern: fjern navn/e-post før noe sendes til Claude. `.env` skal aldri i Git.
- Ny regel = ny sjekk i `sjekk.py` + en testbruker som viser den.
