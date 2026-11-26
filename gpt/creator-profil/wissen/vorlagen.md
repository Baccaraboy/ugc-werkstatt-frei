# vorlagen

## vorlagen/einrichtungs-prompt.md

# Richte mein Creator-Profil ein

<!-- P5a · 25.11.2026 · Mit den Dateien aus dem Download auch ohne installierten Skill einfügen. -->

Nutze die mitgelieferten Teile und das Skript `profil.py`. Suche zuerst mein `profil.json` im Projekt. Habe ich schon eines, lies es und frage nur nach den Angaben, die fehlen oder die ich ändern möchte.

Für mein erstes Profil frag mich nach meinem Grundhonorar und meinen Aufschlägen, meinem Steuerweg und meiner Rücklage. Übernimm meine Angaben und meine Unterlagen. Fehlt eine Pflichtangabe, frage nach und lass den Entwurf bis dahin offen. Nur für einen ausdrücklich gewünschten Probelauf verwende die gekennzeichneten Beispielwerte in einer separaten Arbeitskopie. Danach klären wir meine Themen, Videoarten, Plattformen und die Einstellungen für Aufträge. Für meinen Ton kannst du eigene gesendete Nachrichten auswerten. Büro-Ordner brauche ich nur, wenn ich die Mac-Stationen nutze. Stelle zusammengehörige Fragen gemeinsam, überspringe alles, was ich schon mitgegeben habe.

Zeig mir, was gespeichert werden soll. Speichere mit meiner Zustimmung über `profil.py`, wie in `SKILL.md` bzw. `prompt.md` beschrieben. Im ChatGPT-Wissen heißt der Schreiber ebenfalls `profil.py`. Gib mir die geprüfte Datei fürs Projekt. Verwende dort die gemeinsame Projekt-Anweisung.

## vorlagen/profil.md

# Creator-Profil

<!-- P5a · 25.11.2026 · Ausgabe eines gespeicherten Profils. Die Stilfelder stehen im Abschnitt ton der geprüften Datei. -->

Creator-Profil fertig.

{{Ein Satz zur Neuanlage oder zur bestätigten Änderung.}}

Datei: profil.json

Hänge die vollständige geprüfte Datei an. Kann der Chat nur Text zurückgeben, setze den unveränderten Inhalt aus dem Schreiber in einen JSON-Block.

Für den Stilteil gelten diese sieben Felder:

| Feld        | Eintrag                                                      |
| ----------- | ------------------------------------------------------------ |
| anrede      | Beobachtete Anrede und Begrüßung ohne Namen                  |
| ton         | Schreibweise mit kurzem Originalausschnitt                   |
| satzlaenge  | Länge oder Wechsel mit einem kurzen Beleg                    |
| wendungen   | Wortlaut wiederkehrender Wendungen als Liste                 |
| emojis      | Selbst geschriebene Zeichen oder Hinweis auf fehlenden Beleg |
| grussformel | Abschiedsgruß ohne Namen                                     |
| nie         | Ausdrücklich ausgeschlossene Schreibweisen als Liste         |

Eine fehlende Beobachtung wird als „nicht belegt“ gekennzeichnet. Unbelegte Listen bleiben leer. Die zwei Probesätze stehen in der Chatantwort außerhalb der Datei.

## vorlagen/projekt-anweisung.md

# Mein Büro

<!-- P5a · 25.11.2026 · Diese Anweisung einmal im Claude- oder ChatGPT-Projekt einfügen. -->

Lies zu Beginn jedes Auftrags mein `profil.json` im Projekt. Verwende meine Preise, meinen Steuerweg, meinen Ton und meine Einstellungen. Führe für Beträge, Steuern und Fristen immer das passende Skript des Produkts aus. Fehlt es, lass das Ergebnis offen. Für einen echten Auftrag nimm meine Angaben aus dem Profil, meinen Unterlagen oder dem Auftrag. Fehlt eine benötigte Angabe oder ist sie als Beispiel gekennzeichnet, frage nach meinem Wert und lass das davon abhängige Ergebnis offen. Nur für einen ausdrücklich gewünschten Probelauf verwende die gekennzeichneten Beispielwerte der Werkstatt in einer separaten Arbeitskopie. Änderungen an meinem Profil speichert ausschließlich das Creator-Profil auf meinen Wunsch. Jeder Auftrag bekommt seinen eigenen Chat in diesem Büro.

## Paket im ChatGPT-Projekt öffnen

Öffne im Rechenwerkzeug die angehängte Originaldatei des passenden Produkts. Für Einrichtung und Änderungen am Profil ist das `werkstatt-creator-profil.txt`, für Angebote, Aufträge und Zahlungen `werkstatt-auftraege-und-geld.txt`, für Briefing, Skript und Schnitt `werkstatt-video-vorgabe.txt`. Die TXT-Dateien enthalten JSON. Übergib dieser Funktion den tatsächlichen Pfad der gewählten Projektdatei:

```python
import json
from pathlib import Path
from tempfile import mkdtemp

def werkstatt_oeffnen(paketdatei):
    paket = json.loads(Path(paketdatei).read_text(encoding="utf-8"))
    ordner = Path(mkdtemp()) / "wissen"
    ordner.mkdir()
    for name, inhalt in paket["dateien"].items():
        if not name or name.startswith(".") or Path(name).name != name:
            raise ValueError("Ungültiger Dateiname im Paket.")
        (ordner / name).write_bytes(inhalt.encode("utf-8"))
    return paket["anweisung"], ordner
```

Lies die zurückgegebene Anweisung. In diesem Ordner gilt die darin beschriebene flache GPT-Ablage. Starte jedes benötigte Skript mit Python als eigenen Prozess im zugehörigen Ordner. Persönliche Dateien wie `profil.json` und Aufträge liegen separat; übergib ihren jeweiligen Arbeitskopienpfad und gib Änderungen als Datei zurück. Öffne die Paketdatei nach einem Neustart des Rechenwerkzeugs erneut. Wenn das Original im Rechenwerkzeug fehlt, bitte um die TXT-Datei als Chat-Anhang. Verwende nur die vollständigen mitgelieferten Skripte.
