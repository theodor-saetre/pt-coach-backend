"""
Lag en ukeplan for én bruker.

Eksempler (i terminalen, fra prosjektmappen):
    py lag_plan.py testbrukere/01_nybegynner_8km_60min.json --uten-ai
    py lag_plan.py testbrukere/02_sterk_loper_8km_30min.json
    py lag_plan.py meg.json --json        (skriver hele svaret som JSON)
"""

import argparse
import json
import sys
from pathlib import Path

from dotenv import load_dotenv

from coach import lag_ukeplan
from visning import plan_som_tekst

if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8")  # æøå i Windows-terminalen


def main() -> None:
    load_dotenv()
    p = argparse.ArgumentParser(description="Lag ukeplan med PT-coachen")
    p.add_argument("fil", help="JSON-fil med brukerbilde (se docs/avtale.md)")
    p.add_argument("--uten-ai", action="store_true", help="Bare regler, ingen API-kall (gratis)")
    p.add_argument("--json", action="store_true", help="Skriv hele svaret som JSON")
    p.add_argument("--modell", help="Overstyr modellen, f.eks. claude-haiku-5-5")
    a = p.parse_args()

    bilde = json.loads(Path(a.fil).read_text(encoding="utf-8"))
    resultat = lag_ukeplan(bilde, uten_ai=a.uten_ai, modell=a.modell)
    if a.json:
        print(json.dumps(resultat, ensure_ascii=False, indent=2))
    else:
        print(plan_som_tekst(resultat, Path(a.fil).stem))


if __name__ == "__main__":
    main()
