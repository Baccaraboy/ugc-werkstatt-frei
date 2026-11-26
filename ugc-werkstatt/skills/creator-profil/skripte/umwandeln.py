# P3a · 24.11.2026 · Eine Formatdatei älterer Fassung in die heutige bringen: ein Skript für alle drei Formate (Profil,
# Auftrag, Video-Vorgabe), je Format eigene Schritte. Vorher stand es als umwandeln.py nur im Paket «Aufträge & Geld» (P2b, nur
# Auftrag); seit P3a liegt es einmal in formate/umwandeln.py und steckt byte-gleich in jedem Paket, das eine Formatdatei liest
# oder schreibt (QUELLEN.json, paketkopien). Regel 8: Ein Update ersetzt nur Wissen, die Datei des Creators wird umgewandelt,
# nie ersetzt. Die Datei sagt selbst, welches Format sie hat (`format`) und in welcher Fassung (`formatfassung`).
#   Auftrag      1 -> 2: `nutzungsrechte.laufzeit_monate` und `exklusivitaet.monate` werden das Feld `dauer` (P2b).
#                2 -> 3: `termine.material_am` bleibt für ältere Aufträge offen.
#                3 -> 4: Belegte Buchungen oder ein ausdrücklich ungeklärter Stand.
#   Profil       1 -> 2: neues Feld `sprechtempo` (null, bis das Tempo des Creators gemessen ist) (P3a).
#   Video-Vorgabe: heute Fassung 1, noch kein Schritt.
# Spätere Fassungen kommen als weiterer Schritt in SCHRITTE dazu; FASSUNGEN nennt die heutige je Format.
# Aufruf: python3 skripte/umwandeln.py --datei <datei>.json   (gibt die neue Fassung aus, schreibt nichts)
# Geschrieben wird nur durch den einen Schreiber des Formats (auftrag.py, vorgabe.py), nach der Prüfung gegen das Schema.
# Nur Standardbibliothek.
import argparse
import copy
import json
import re
import sys

FASSUNGEN = {"profil": 2, "auftrag": 4, "video-vorgabe": 1}


def auftrag_1_auf_2(auftrag):
    rechte = auftrag.get("nutzungsrechte")
    if isinstance(rechte, dict):
        monate = rechte.pop("laufzeit_monate", None)
        rechte["dauer"] = {"art": "laufzeit", "menge": monate, "einheit": "monate"} if monate else {"art": "unbefristet"}
        exklusiv = rechte.get("exklusivitaet")
        if isinstance(exklusiv, dict):
            # Fassung 1 zählte die Exklusivität ab dem Start der Nutzung; jetzt hat sie einen eigenen Start.
            exklusiv.setdefault("start", rechte.get("start"))
            exklusiv["dauer"] = {"art": "laufzeit", "menge": exklusiv.pop("monate"), "einheit": "monate"}
    return auftrag


def auftrag_2_auf_3(auftrag):
    auftrag.setdefault("termine", {})["material_am"] = None
    return auftrag


def auftrag_3_auf_4(auftrag):
    r = auftrag.get("rechnung")
    if not r or "zahlungen" in r:
        return auftrag
    # Nur die vom früheren Schreiber erzeugte Rechnungsnotiz belegt, dass beim Stellen
    # keine Anzahlung vermerkt war. Freitext enthält keine verlässlichen Buchungsdaten.
    historie = auftrag.get("verlauf", [])
    ausstellung = [e.get("notiz") or "" for e in historie if e.get("schritt") == "rechnung"]
    buchungen = [e for e in historie if e.get("schritt") == "zahlung"]
    r["zahlungen"] = None
    muster = r"Rechnung " + re.escape(str(r.get("nummer"))) + r" gestellt, Rechnungsbetrag [0-9.]+,[0-9]{2} €"
    if not ausstellung or not re.fullmatch(muster, ausstellung[-1]):
        return auftrag
    if not buchungen and r["status"] in ("gestellt", "ueberfaellig") and not r.get("zahlungsdatum"):
        r["zahlungen"] = []
    elif (r["status"] == "bezahlt" and r.get("zahlungsdatum") and r.get("brutto") is not None
          and len(buchungen) == 1 and buchungen[0].get("notiz") == "Zahlung eingegangen am " + r["zahlungsdatum"]):
        r["zahlungen"] = [{"am": r["zahlungsdatum"], "betrag": r["brutto"]}] if r["brutto"] else []
    return auftrag


def profil_1_auf_2(profil):
    # Ohne persönliche Messung bleibt das Tempo offen.
    profil.setdefault("sprechtempo", None)
    return profil


SCHRITTE = {
    "profil": {1: profil_1_auf_2},
    "auftrag": {1: auftrag_1_auf_2, 2: auftrag_2_auf_3, 3: auftrag_3_auf_4},
    "video-vorgabe": {},
}


def fassung(format_):
    """Die heutige Fassung eines Formats."""
    if format_ not in FASSUNGEN:
        raise ValueError("Das Format " + str(format_) + " kennt dieses Skript nicht (" + ", ".join(FASSUNGEN) + ").")
    return FASSUNGEN[format_]


def umwandeln(datei, format_=None):
    """Gibt die Datei in der heutigen Fassung ihres Formats zurück; der Eingang bleibt unverändert.

    Das Format steht in der Datei (`format`); `format_` gilt nur, wenn die Datei es nicht nennt."""
    art = datei.get("format", format_) if isinstance(datei, dict) else None
    heute = fassung(art)
    aktuell = datei.get("formatfassung")
    if not isinstance(aktuell, int) or isinstance(aktuell, bool) or not 1 <= aktuell <= heute:
        raise ValueError("Die Fassung " + str(aktuell) + " der Datei vom Format " + art + " kennt dieses Paket nicht (1 bis " + str(heute) + ").")
    neu = copy.deepcopy(datei)
    while aktuell < heute:
        neu = SCHRITTE[art][aktuell](neu)
        aktuell += 1
        neu["formatfassung"] = aktuell
    return neu


HILFE = """Bringt eine Formatdatei (Profil, Auftrag oder Video-Vorgabe) älterer Fassung in die heutige und gibt sie aus;
die Datei selbst bleibt.
  python3 skripte/umwandeln.py --datei auftraege/<kennung>.json
Zum Schreiben nimm den Schreiber des Formats, zum Beispiel: python3 skripte/auftrag.py umwandeln --datei auftraege/<kennung>.json"""


def main(argumente=None):
    parser = argparse.ArgumentParser(description=HILFE, formatter_class=argparse.RawDescriptionHelpFormatter, prog="umwandeln.py", add_help=False)
    parser.add_argument("--hilfe", action="help", help="diese Hilfe zeigen")
    parser.add_argument("--datei", required=True)
    optionen = parser.parse_args(argumente)
    try:
        with open(optionen.datei, encoding="utf-8") as datei:
            ergebnis = umwandeln(json.load(datei))
    except (ValueError, OSError, KeyError, TypeError) as fehler:
        print(json.dumps({"fehler": [str(fehler)]}, ensure_ascii=False))
        return 1
    print(json.dumps(ergebnis, ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    sys.exit(main())
