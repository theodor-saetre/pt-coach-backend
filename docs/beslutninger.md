# Beslutninger og bakgrunn

Sammendrag av planleggingen før koden ble skrevet (oktober 2026).

## Produktet
- Kommersiell app for vanlige mosjonister: styrke, utholdenhet eller holde formen. Skal være enkel nok for nybegynnere og ha nok innsikt for «Strava-gjengen».
- Samler det folk i dag bruker flere apper til: treningsdagbok, plan, kosthold og tracking.
- Kjernen er AI-coachen, «lavterskel PT». Gamification finnes, men er ikke hovedfokus: streak og milepæler. Hviledager og sykedager bryter ikke streaken.
- Brukeren velger selv: med eller uten plan, trening og/eller kosthold, og hvor mye tall (Enkel / Standard / Detaljert). Enkel viser ingen kalorier.
- Det skal være lett å gjøre noe annet enn planen: én «+»-knapp med ett tekstfelt («2 brødskiver og 1 time padel»), og AI-en sorterer i mat, trening og vekt.
- Kosthold: bare dagsmål (kcal, protein, karbo, fett) og hva som er igjen i dag. Ingen matretter foreløpig. Allergier gir «kan inneholde»-varsel ved strekkode, aldri 100 %-garantier. Bildeestimat av mat må bekreftes og kan justeres.
- Morgen- og kveldsinnsjekk som standard (kan endres). «Sliten» gir kortere og roligere økt, «syk» gir hvile.
- Styrke logges i appen: kg og reps per sett. Dobbel progresjon (8–10 reps: alle sett på 10 gir mer vekt, flere sett under 8 gir litt lettere).
- Løping tilpasses nivå ut fra tempo (8 km på 30 min og på 60 min gir helt ulike planer) og pulssoner (Karvonen).

## Design (klikkbar prototype laget i claude.ai)
- Rødt, hvitt og marineblått (#C8102E, #FFFFFF, #00205B), inspirert av Olympiatoppen. «Skarp» stil: rette kanter, smal versal-skrift (Barlow Condensed), hele fargeflater.
- «I dag»: rød topp med dagens økt (eller blå ved hviledag), blått felt med «mat igjen i dag», neste måltid under. Resten gjemt bak «Vis alt».

## Data fra klokker
- Første versjon: Apple Health (Apple Watch fullt, Garmin via Garmin Connect → Apple Health, men med lite detaljer).
- Garmins utviklerprogram er bare for bedrifter og har pauset nye søknader (2026). Terra (fra ca. 399–499 USD/mnd) er alternativet for full Garmin-data og sending av økter til klokka.
- Strava passer ikke: Strava forbyr bruk av API-data i AI, maks 7 dagers lagring.
- Sending av planlagte økter til Apple Watch: WorkoutKit (iOS 17+).

## Teknikk
- Ingen Mac. Appen bygges senere med Expo/React Native, med skybygg (EAS) til TestFlight. Krever Apple Developer-konto (99 USD/år).
- AI: Claude via API, kalt fra server, aldri direkte fra appen. Modellen er byttbar på ett sted (`coach/ai.py`).
- Database senere: Supabase i EU.

## Personvern og trygghet
- Helsedata = særlige kategorier (GDPR): eget samtykke, minst mulig data, sletting med ett trykk, databehandleravtaler, lagring i EU. Ingen medisinske råd. Jurist eller personvernrådgiver før eksterne testere.

## Neste steg
1. Kjør alle testbrukerne med Claude, les rapporten som en PT og forbedre instruksen.
2. Bruk coachen på meg selv i en uke (`meg.json`).
3. Coach-chat som agent med reglene som verktøy.
4. Tolking av fritekst («ett felt») og bildeestimat av mat.
5. Legg coachen ut som en nettjeneste (FastAPI) i EU.
6. Bygg appen (Expo), koble til Apple Health, test med 10 personer i 2 uker via TestFlight.
