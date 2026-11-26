# P5a · 25.11.2026 · Ein Schreiber für profil.json im Büro und im Rechenwerkzeug des Chats.
import argparse
import json
import os
import sys
import tempfile
from datetime import date
from pathlib import Path

import daten
from schemapruefer import Pruefer
from umwandeln import umwandeln


def laden(pfad):
    wert = json.loads(pfad.read_text(encoding="utf-8"))
    if not isinstance(wert, dict):
        raise ValueError("Erwartet wird ein JSON-Objekt.")
    json.dumps(wert, allow_nan=False)
    return wert


def profil_lesen(ziel):
    alt = laden(ziel)
    if alt.get("format") != "profil":
        raise ValueError("Die Datei enthält kein Creator-Profil.")
    return umwandeln(alt)


def pruefen(profil):
    preis = daten.regel("meine-preise.schema")
    pruefer = Pruefer(daten.format_("profil.schema.json"), daten.format_("gemeinsam.schema.json"),
                      {"ratecard.schema.json": preis})
    fehler = pruefer.pruefe(profil)
    if fehler:
        raise ValueError("\n".join(fehler))


def ergaenzen(bisher, antworten):
    ergebnis = bisher.copy()
    for feld, wert in antworten.items():
        if isinstance(wert, dict) and isinstance(bisher.get(feld), dict):
            wert = ergaenzen(bisher[feld], wert)
        ergebnis[feld] = wert
    return ergebnis


def bearbeiten(aktion, ziel, antworten):
    if aktion == "lesen":
        profil = profil_lesen(ziel)
        pruefen(profil)
        return profil
    # Zwei gleichzeitige Änderungswünsche sollen einander nicht überschreiben.
    sperre = ziel.with_name(ziel.name + ".sperre")
    try:
        sperre.mkdir()
    except FileExistsError:
        raise ValueError("Das Profil wird gerade bearbeitet. Prüfe den Stand und versuche es erneut.")
    try:
        if aktion == "anlegen":
            if ziel.exists():
                raise ValueError("Das Profil ist schon vorhanden. Lies es zuerst.")
            neu = antworten
        else:
            if {"format", "formatfassung", "angelegt_am", "geaendert_am"} & antworten.keys():
                raise ValueError("Format, Fassung und Datumsfelder verwaltet das Paket.")
            alt = profil_lesen(ziel)
            neu = ergaenzen(alt, antworten)
            pruefen(neu)
            if neu == alt:
                return alt
            neu["geaendert_am"] = date.today().isoformat()
        pruefen(neu)
        temp = None
        try:
            with tempfile.NamedTemporaryFile("w", encoding="utf-8", dir=ziel.parent, delete=False) as datei:
                temp = Path(datei.name)
                json.dump(neu, datei, ensure_ascii=False, allow_nan=False, indent=2)
                datei.write("\n")
            if aktion == "anlegen":
                os.link(temp, ziel)
            else:
                os.replace(temp, ziel)
        finally:
            if temp is not None:
                temp.unlink(missing_ok=True)
        return neu
    finally:
        sperre.rmdir()


def main():
    parser = argparse.ArgumentParser(add_help=False, description="Liest ein Profil, legt es neu an oder ändert nur bestätigte Felder. Ein alter Stand wird beim Lesen im Speicher umgewandelt.")
    parser.add_argument("--hilfe", action="help")
    parser.add_argument("aktion", choices=["lesen", "anlegen", "aendern"])
    parser.add_argument("--datei", required=True, type=Path, help="Profil im Büro oder Arbeitskopie im Chat")
    parser.add_argument("--eingabe", type=Path, help="Für anlegen das ganze neue Profil, für aendern nur geänderte Felder als JSON")
    args = parser.parse_args()
    if (args.aktion == "lesen") != (args.eingabe is None):
        parser.error("--eingabe nur bei anlegen und aendern angeben")
    try:
        profil = bearbeiten(args.aktion, args.datei, laden(args.eingabe) if args.eingabe else None)
        print(json.dumps(profil, ensure_ascii=False, indent=2))
    except (OSError, ValueError) as fehler:
        print(json.dumps({"fehler": str(fehler).splitlines()}, ensure_ascii=False))
        return 1
    return 0


if __name__ == "__main__":
    sys.exit(main())
