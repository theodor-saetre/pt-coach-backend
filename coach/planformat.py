"""
PLANFORMATET – det faste formatet AI-en må svare i.

Claude får dette skjemaet og kan bare svare med gyldig JSON som passer.
Merk at det IKKE er kalorier her: maten regner koden ut selv etterpå,
fra regelmotoren og øktene AI-en valgte. Da kan ikke AI-en regne feil på mat.
"""

OKT_TYPER = ["lop", "styrke", "sykkel", "gange", "padel", "annet", "hvile"]
INTENSITETER = ["hvile", "rolig", "moderat", "hard"]

PLAN_SKJEMA = {
    "type": "object",
    "properties": {
        "pt_melding": {
            "type": "string",
            "description": "2–4 setninger til brukeren, som en vennlig PT: hva uka handler om og hvorfor.",
        },
        "dager": {
            "type": "array",
            "description": "Nøyaktig 7 dager, samme datoer og rekkefølge som i dager_i_planen.",
            "items": {
                "type": "object",
                "properties": {
                    "dato": {"type": "string", "format": "date"},
                    "dag": {"type": "string"},
                    "type": {"type": "string", "enum": OKT_TYPER},
                    "tittel": {"type": "string", "description": "Kort, f.eks. 'Rolig løp' eller 'Hviledag'."},
                    "minutter": {"type": "integer", "description": "0 på hviledager."},
                    "intensitet": {"type": "string", "enum": INTENSITETER},
                    "pulssone": {"type": "string", "description": "F.eks. '2', '1-2', '4'. Tom streng hvis ikke relevant."},
                    "tempo": {"type": "string", "description": "Fra fakta.lop hvis løping og data finnes, ellers tom streng."},
                    "beskrivelse": {"type": "string", "description": "1–2 setninger: hva økta er og hvordan den skal føles."},
                    "ovelser": {
                        "type": "array",
                        "description": "Bare for styrke. Tom liste ellers.",
                        "items": {
                            "type": "object",
                            "properties": {
                                "navn": {"type": "string"},
                                "sett": {"type": "integer"},
                                "reps": {"type": "string", "description": "F.eks. '8-10'."},
                                "kg": {"type": "number", "description": "Fra fakta.styrke hvis øvelsen finnes der. 0 = velg selv / kroppsvekt."},
                                "tips": {"type": "string", "description": "Ett kort teknikktips."},
                            },
                            "required": ["navn", "sett", "reps", "kg", "tips"],
                            "additionalProperties": False,
                        },
                    },
                },
                "required": ["dato", "dag", "type", "tittel", "minutter", "intensitet", "pulssone", "tempo", "beskrivelse", "ovelser"],
                "additionalProperties": False,
            },
        },
        "hvorfor": {
            "type": "array",
            "description": "2–4 korte punkter som forklarer valgene, med henvisning til tallene i fakta.",
            "items": {"type": "string"},
        },
        "trygghet": {
            "type": "string",
            "description": "Ta med alle fakta.energi.varsler og fakta.i_dag.melding med egne ord. Tom streng hvis ingen.",
        },
    },
    "required": ["pt_melding", "dager", "hvorfor", "trygghet"],
    "additionalProperties": False,
}
