# P3a · 24.11.2026 · Der kleine Schema-Prüfer der Werkstatt: ein Baustein für alle Formate (Regel 8: ein Baustein je Aufgabe).
# Vorher steckte er in auftrag.py (P2b); seit P3a liegt er einmal in formate/schemapruefer.py und steckt byte-gleich in jedem
# Paket, das eine Formatdatei schreibt (QUELLEN.json, paketkopien). Er liest nur die Stichwörter, die die Schemas der
# Werkstatt nutzen; ein unbekanntes Stichwort oder ein fremder Verweis bricht laut ab, statt still zu bestehen. Verweise gehen
# nur nach gemeinsam.schema.json und, wo ein Schema es verlangt, nach einem Nachbarn (P3b: plan.schema.json, das Planformat des
# Schnitts). Nur die Standardbibliothek.
import json
import re

IGNORIERT = {"$schema", "$id", "$comment", "title", "description", "default", "x-tabelle", "format", "$defs"}


class Schemafehler(ValueError):
    pass


def _ist(wert, typ):
    if typ == "object":
        return isinstance(wert, dict)
    if typ == "array":
        return isinstance(wert, list)
    if typ == "string":
        return isinstance(wert, str)
    if typ == "boolean":
        return isinstance(wert, bool)
    if typ == "null":
        return wert is None
    if typ == "integer":
        return isinstance(wert, int) and not isinstance(wert, bool) or (isinstance(wert, float) and wert.is_integer())
    if typ == "number":
        return isinstance(wert, (int, float)) and not isinstance(wert, bool)
    raise ValueError("Unbekannter Typ im Schema: " + typ)


class Pruefer:
    def __init__(self, schema, gemeinsam, nachbarn=None):
        """nachbarn: weitere Schemas, auf die verwiesen werden darf, unter ihrem Dateinamen (zum Beispiel plan.schema.json)."""
        self.schema = schema
        self.gemeinsam = gemeinsam
        self.nachbarn = nachbarn or {}

    def aufloesen(self, ref, von):
        """Gibt (Teilschema, Wurzel) zurück; ein Verweis ohne Datei bleibt in der Datei, in der er steht."""
        ziel, _, zeiger = ref.partition("#")
        datei = ziel.rsplit("/", 1)[-1]
        if ziel and datei != "gemeinsam.schema.json" and datei not in self.nachbarn:
            raise ValueError("Der Verweis " + ref + " kennt dieser Prüfer nicht.")
        wurzel = von if not ziel else self.gemeinsam if datei == "gemeinsam.schema.json" else self.nachbarn[datei]
        teilschema = wurzel
        for teil in [t for t in zeiger.split("/") if t]:
            teilschema = teilschema[teil]
        return teilschema, wurzel

    def pruefe(self, wert, schema=None, pfad="", wurzel=None):
        schema = self.schema if schema is None else schema
        wurzel = self.schema if wurzel is None else wurzel
        fehler = []
        for stichwort, soll in schema.items():
            if stichwort in IGNORIERT:
                continue
            if stichwort == "$ref":
                ziel, neue_wurzel = self.aufloesen(soll, wurzel)
                fehler += self.pruefe(wert, ziel, pfad, neue_wurzel)
            elif stichwort == "type":
                if not any(_ist(wert, t) for t in (soll if isinstance(soll, list) else [soll])):
                    fehler.append(f"{pfad or '/'}: muss vom Typ {soll} sein")
            elif stichwort == "const":
                if wert != soll or type(wert) is not type(soll):
                    fehler.append(f"{pfad or '/'}: muss {json.dumps(soll, ensure_ascii=False)} sein")
            elif stichwort == "enum":
                if wert not in soll:
                    fehler.append(f"{pfad or '/'}: muss eines von {soll} sein")
            elif stichwort in ("minimum", "maximum", "exclusiveMinimum", "multipleOf"):
                if _ist(wert, "number"):
                    if stichwort == "minimum" and wert < soll:
                        fehler.append(f"{pfad}: höchstens/mindestens {soll}, ist {wert}")
                    elif stichwort == "maximum" and wert > soll:
                        fehler.append(f"{pfad}: höchstens {soll}, ist {wert}")
                    elif stichwort == "exclusiveMinimum" and wert <= soll:
                        fehler.append(f"{pfad}: muss größer als {soll} sein")
                    elif stichwort == "multipleOf" and abs(round(wert / soll) * soll - wert) > 1e-6:
                        fehler.append(f"{pfad}: muss ein Vielfaches von {soll} sein")
            elif stichwort in ("minLength", "maxLength", "pattern"):
                if isinstance(wert, str):
                    if stichwort == "minLength" and len(wert) < soll:
                        fehler.append(f"{pfad}: zu kurz")
                    elif stichwort == "maxLength" and len(wert) > soll:
                        fehler.append(f"{pfad}: zu lang (höchstens {soll} Zeichen)")
                    elif stichwort == "pattern" and not re.search(soll, wert):
                        fehler.append(f"{pfad}: hat nicht die verlangte Form")
            elif stichwort in ("minItems", "maxItems", "uniqueItems", "items"):
                if isinstance(wert, list):
                    if stichwort == "minItems" and len(wert) < soll:
                        fehler.append(f"{pfad}: braucht mindestens {soll} Einträge")
                    elif stichwort == "maxItems" and len(wert) > soll:
                        fehler.append(f"{pfad}: höchstens {soll} Einträge")
                    elif stichwort == "uniqueItems" and soll and len({json.dumps(e, sort_keys=True) for e in wert}) != len(wert):
                        fehler.append(f"{pfad}: Einträge doppelt")
                    elif stichwort == "items":
                        for i, eintrag in enumerate(wert):
                            fehler += self.pruefe(eintrag, soll, f"{pfad}/{i}", wurzel)
            elif stichwort == "required":
                if isinstance(wert, dict):
                    fehler += [f"{pfad}/{name}: fehlt" for name in soll if name not in wert]
            elif stichwort == "dependentRequired":
                if isinstance(wert, dict):
                    for ausloeser, namen in soll.items():
                        if ausloeser in wert:
                            fehler += [f"{pfad}/{name}: fehlt für {ausloeser}" for name in namen if name not in wert]
            elif stichwort == "properties":
                if isinstance(wert, dict):
                    for name, teil in soll.items():
                        if name in wert:
                            fehler += self.pruefe(wert[name], teil, f"{pfad}/{name}", wurzel)
            elif stichwort == "additionalProperties":
                if isinstance(wert, dict):
                    fremd = [name for name in wert if name not in schema.get("properties", {})]
                    if soll is False:
                        fehler += [f"{pfad}/{name}: gibt es im Format nicht" for name in fremd]
                    elif isinstance(soll, dict):
                        for name in fremd:
                            fehler += self.pruefe(wert[name], soll, f"{pfad}/{name}", wurzel)
            elif stichwort == "propertyNames":
                if isinstance(wert, dict):
                    for name in wert:
                        if self.pruefe(name, soll, pfad, wurzel):
                            fehler.append(f"{pfad}/{name}: der Name stimmt nicht")
            elif stichwort in ("minProperties", "maxProperties"):
                if isinstance(wert, dict):
                    if stichwort == "minProperties" and len(wert) < soll:
                        fehler.append(f"{pfad or '/'}: braucht mindestens {soll} Einträge")
                    elif stichwort == "maxProperties" and len(wert) > soll:
                        fehler.append(f"{pfad or '/'}: höchstens {soll} Einträge")
            elif stichwort == "oneOf":
                treffer = sum(not self.pruefe(wert, teil, pfad, wurzel) for teil in soll)
                if treffer != 1:
                    fehler.append(f"{pfad or '/'}: passt auf {treffer} statt genau eine der Möglichkeiten")
            elif stichwort == "if":
                if not self.pruefe(wert, soll, pfad, wurzel):
                    if "then" in schema:
                        fehler += self.pruefe(wert, schema["then"], pfad, wurzel)
                elif "else" in schema:
                    fehler += self.pruefe(wert, schema["else"], pfad, wurzel)
            elif stichwort in ("then", "else"):
                continue
            else:
                raise Schemafehler("Das Schemastichwort " + stichwort + " kennt dieser Prüfer nicht.")
        return fehler


def main():
    import argparse
    import sys
    from pathlib import Path

    parser = argparse.ArgumentParser(add_help=False, description="Prüft eine JSON-Datei gegen ein Schema der Werkstatt.")
    parser.add_argument("--hilfe", action="help", help="diese Hilfe zeigen")
    parser.add_argument("--datei", required=True, help="die JSON-Datei, die geprüft wird")
    parser.add_argument("--schema", required=True, help="das Schema (…schema.json), gegen das geprüft wird")
    parser.add_argument("--gemeinsam", required=True, help="gemeinsam.schema.json, auf das die Schemas verweisen")
    parser.add_argument("--plan", help="plan.schema.json, wenn das Schema darauf verweist (der Schnittteil der Video-Vorgabe)")
    args = parser.parse_args()
    laden = lambda pfad: json.loads(Path(pfad).read_text(encoding="utf-8"))  # noqa: E731
    try:
        nachbarn = {"plan.schema.json": laden(args.plan)} if args.plan else None
        fehler = Pruefer(laden(args.schema), laden(args.gemeinsam), nachbarn).pruefe(laden(args.datei))
    except (OSError, ValueError) as ausnahme:
        print(json.dumps({"fehler": [str(ausnahme)]}, ensure_ascii=False))
        sys.exit(1)
    print(json.dumps({"fehler": fehler}, ensure_ascii=False, indent=2))
    sys.exit(1 if fehler else 0)


if __name__ == "__main__":
    main()
