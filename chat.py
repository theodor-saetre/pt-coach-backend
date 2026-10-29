"""
Snakk med coachen. Foreløpig forstår den dagsformen din: syk, frisk igjen, sliten eller pigg.

    python chat.py testbrukere/06_syk_i_dag.json                     (bruker Claude)
    python chat.py testbrukere/06_syk_i_dag.json --uten-ai           (gratis, enkle stikkord)
    python chat.py testbrukere/06_syk_i_dag.json --melding "jeg er frisk nå"
    python chat.py meg.json --lagre                                  (lagrer dagsformen i fila)

Skriv q eller trykk Enter på tom linje for å avslutte.
"""

import argparse
import json
import sys
from pathlib import Path

from dotenv import load_dotenv

from coach import lag_ukeplan
from coach.chat import oppdater_bilde, tolk_melding
from visning import plan_som_tekst

if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8")


def svar_pa(tekst: str, bilde: dict, a: argparse.Namespace, fil: Path) -> dict:
    tolkning = tolk_melding(tekst, uten_ai=a.uten_ai, modell=a.modell)
    print(f"Coach: {tolkning['svar']}\n")
    if tolkning["dagsform"] == "ingen":
        return bilde
    bilde = oppdater_bilde(bilde, tolkning["dagsform"])
    if a.lagre:
        fil.write_text(json.dumps(bilde, ensure_ascii=False, indent=2), encoding="utf-8")
    print(plan_som_tekst(lag_ukeplan(bilde, uten_ai=a.uten_ai, modell=a.modell), "Ny plan"))
    return bilde


def main() -> None:
    load_dotenv()
    p = argparse.ArgumentParser(description="Snakk med PT-coachen")
    p.add_argument("fil", help="JSON-fil med brukerbilde (se docs/avtale.md)")
    p.add_argument("--uten-ai", action="store_true", help="Bare stikkord og regler, ingen API-kall (gratis)")
    p.add_argument("--melding", help="Send én melding og avslutt")
    p.add_argument("--lagre", action="store_true", help="Lagre oppdatert dagsform tilbake i fila")
    p.add_argument("--modell", help="Overstyr modellen")
    a = p.parse_args()

    fil = Path(a.fil)
    bilde = json.loads(fil.read_text(encoding="utf-8"))
    if a.melding:
        svar_pa(a.melding, bilde, a, fil)
        return
    while (tekst := input("Du: ").strip()) and tekst.lower() != "q":
        bilde = svar_pa(tekst, bilde, a, fil)


if __name__ == "__main__":
    main()
