# Avtalen mellom appen og AI-coachen

Dette er formatet appen skal sende til coachen, og det coachen sender tilbake.
Hold deg til det, så kan appen og coachen bygges hver for seg og kobles sammen senere.

## Inn: brukerbildet

Appen samler dette fra profilen, Apple Health og det brukeren har registrert.
Eksempel: `meg.json` og filene i `testbrukere/`.

| Felt | Innhold |
|---|---|
| `bruker.alder`, `kjonn`, `vekt_kg`, `hoyde_cm` | Til energiberegning. `kjonn`: `mann`, `kvinne` eller `ukjent` |
| `bruker.malvekt_kg` | Tall eller `null` |
| `bruker.mal` | `utholdenhet`, `styrke`, `holde_formen` eller `ned_i_vekt` |
| `bruker.niva_egenvurdering` | `nybegynner`, `middels` eller `erfaren` |
| `bruker.okter_per_uke`, `minutter_per_okt` | Hvor mye tid brukeren har |
| `bruker.utstyr` | F.eks. `["treningssenter"]` eller `["ingen"]` |
| `bruker.bruk` | `plan`, `trening`, `kosthold` (sann/usann) og `tall`: `enkel`, `standard` eller `detaljert` |
| `puls.hvilepuls`, `puls.makspuls` | Fra klokka. `makspuls` kan være `null` (estimeres) |
| `okter_siste_6_uker[]` | `dato`, `type` (`lop`, `styrke`, `sykkel`, `padel`, `fotball`, `gange`, `annet`), `minutter`, `km`, `snittpuls`, `rpe` (1–10, hvor tungt det føltes). Ukjent = `null` |
| `styrke_logg[]` | `dato`, `ovelse`, `kg`, `reps` (liste, ett tall per sett). Valgfritt: `rep_fra`, `rep_til`, `steg_kg` |
| `vekt_logg[]` | `dato`, `kg` |
| `innsjekk_i_dag` | `folelse` (`pigg`, `ok`, `sliten`, `syk`) og `sovn` (`god`, `ok`, `darlig`), eller `null` |
| `dato_i_dag` | `ÅÅÅÅ-MM-DD` |

Navn, e-post og telefon fjernes før noe sendes til Claude.

## Ut: resultatet

```json
{
  "godkjent": true,
  "forsok": 1,
  "modell": "claude-sonnet-5-5",
  "plan": {
    "pt_melding": "Kort melding fra PT-en",
    "dager": [
      {
        "dato": "2026-10-29", "dag": "torsdag",
        "type": "lop", "tittel": "Rolig løp", "minutter": 40,
        "intensitet": "rolig", "pulssone": "2", "tempo": "6:10/km–6:40/km",
        "beskrivelse": "Du skal kunne prate hele veien.",
        "ovelser": [],
        "kosthold": {"kcal": 2900, "protein_g": 112, "karbo_g": 380, "fett_g": 90, "herav_trening_kcal": 420}
      }
    ],
    "hvorfor": ["..."],
    "trygghet": "Varsler brukeren må se, eller tom streng"
  },
  "fakta": { "...alle tall fra regelmotoren..." },
  "feil_underveis": []
}
```

- `dager` har alltid 7 dager, og dag 1 er i dag.
- For styrke inneholder `ovelser` `navn`, `sett`, `reps` (f.eks. `"8-10"`), `kg` (0 = velg selv) og `tips`.
- `kosthold` regnes ut av koden, ikke av AI-en. Den mangler hvis brukeren har skrudd av kosthold.
- Er `godkjent` usann, skal appen vise en enkel reserveplan (`py lag_plan.py ... --uten-ai`) i stedet.
