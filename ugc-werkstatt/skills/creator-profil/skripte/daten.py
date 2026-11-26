# P2b · 23.11.2026 · Wo die Daten der Skripte liegen: Regeln als JSON, die Formate der Werkstatt.
# Im Paket liegen sie in regeln/ und formate/; im GPT-Wissen liegen alle Dateien flach in einem Ordner (regeln.json trägt
# dann jede Regeldatei unter ihrem Namen, formate.json ebenso die Formate). Die Skripte fragen nur hier, nie selbst.
# Aufruf: python3 skripte/daten.py <name> zeigt eine Regeldatei (zum Nachlesen); --hilfe erklärt es.
import argparse
import json
import sys
from pathlib import Path

ORT = Path(__file__).resolve().parent


def _json(pfad):
    with open(pfad, encoding="utf-8") as datei:
        return json.load(datei)


def regel(name):
    """Die Regeldatei regeln/<name>.json, im GPT-Wissen der Schlüssel <name> in regeln.json."""
    pfad = ORT.parent / "regeln" / (name + ".json")
    if pfad.is_file():
        return _json(pfad)
    for flach in (ORT / "regeln.json", ORT.parent / "regeln.json"):
        if flach.is_file():
            gebuendelt = _json(flach)
            if name in gebuendelt:
                return gebuendelt[name]
    raise ValueError("Die Regel " + name + " gibt es nicht (regeln/" + name + ".json).")


def format_(name):
    """Ein Format der Werkstatt, zum Beispiel auftrag.schema.json oder beispiel-auftrag.json."""
    pfad = ORT.parent / "formate" / name
    if pfad.is_file():
        return _json(pfad)
    schluessel = name[: -len(".json")] if name.endswith(".json") else name
    for flach in (ORT / "formate.json", ORT.parent / "formate.json"):
        if flach.is_file():
            gebuendelt = _json(flach)
            if schluessel in gebuendelt:
                return gebuendelt[schluessel]
    raise ValueError("Das Format " + name + " gibt es nicht (formate/" + name + ").")


def main(argumente=None):
    parser = argparse.ArgumentParser(
        description="Zeigt eine Regeldatei dieses Pakets als JSON, zum Beispiel: python3 skripte/daten.py fristen",
        prog="daten.py",
        add_help=False,
    )
    parser.add_argument("--hilfe", action="help", help="diese Hilfe zeigen")
    parser.add_argument("name", help="Name der Regeldatei ohne .json")
    optionen = parser.parse_args(argumente)
    try:
        print(json.dumps(regel(optionen.name), ensure_ascii=False, indent=2))
    except (ValueError, OSError) as fehler:
        print(json.dumps({"fehler": [str(fehler)]}, ensure_ascii=False))
        return 1
    return 0


if __name__ == "__main__":
    sys.exit(main())
