"""
Kjør alle testbrukerne gjennom coachen og lag en rapport.

    py kjor_tester.py --uten-ai     (gratis, tester reglene og kontrollen)
    py kjor_tester.py               (bruker Claude, koster litt per bruker)

Rapporten havner i resultater/rapport.md. Les den hver gang du endrer instruksen
eller reglene, så ser du om coachen ble bedre eller dårligere.
"""

import argparse
import json
import sys
import time
from pathlib import Path

from dotenv import load_dotenv

from coach import lag_ukeplan
from visning import plan_som_tekst

if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8")


def main() -> None:
    load_dotenv()
    p = argparse.ArgumentParser()
    p.add_argument("--uten-ai", action="store_true")
    p.add_argument("--bare", help="Kjør bare filer som inneholder denne teksten, f.eks. 'syk'")
    a = p.parse_args()

    ut = Path("resultater")
    ut.mkdir(exist_ok=True)
    filer = sorted(Path("testbrukere").glob("*.json"))
    if a.bare:
        filer = [f for f in filer if a.bare in f.name]

    deler, oppsummering = [], []
    for fil in filer:
        start = time.time()
        try:
            r = lag_ukeplan(json.loads(fil.read_text(encoding="utf-8")), uten_ai=a.uten_ai)
        except Exception as feil:  # én feil skal ikke stoppe hele testen
            oppsummering.append((fil.stem, "KRASJ", str(feil)[:80]))
            print(f"KRASJ   {fil.stem}: {feil}")
            continue
        sek = time.time() - start
        status = "OK" if r["godkjent"] else "FEIL"
        info = f"{r['forsok']} forsøk, {sek:.1f} s"
        oppsummering.append((fil.stem, status, info))
        print(f"{status:<7} {fil.stem}  ({info})")
        (ut / f"{fil.stem}.json").write_text(json.dumps(r, ensure_ascii=False, indent=2), encoding="utf-8")
        deler.append(plan_som_tekst(r, fil.stem))

    tabell = ["| Testbruker | Status | Info |", "|---|---|---|"] + [f"| {n} | {s} | {i} |" for n, s, i in oppsummering]
    (ut / "rapport.md").write_text("# Testrapport\n\n" + "\n".join(tabell) + "\n\n" + "\n\n---\n\n".join(deler), encoding="utf-8")
    ok = sum(1 for _, s, _ in oppsummering if s == "OK")
    print(f"\n{ok} av {len(oppsummering)} godkjent. Rapport: resultater/rapport.md")


if __name__ == "__main__":
    main()
