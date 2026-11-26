"""Prüft die öffentliche Werkstatt-Lieferung und übernimmt nur ihre Produktdateien."""

import argparse
import hashlib
import json
from pathlib import Path
import re
import shutil
import stat
import sys
import tempfile
from urllib.parse import urlsplit
from urllib.request import HTTPRedirectHandler, build_opener
from zipfile import BadZipFile, ZipFile

QUELLE = "https://marius-ugc.de/werkstatt/frei/werkstatt-frei.zip"
MAX_ZIP = 32 * 1024 * 1024
MAX_INHALT = 64 * 1024 * 1024
FASSUNG = r"[0-9]+\.[0-9]+(?:\.[0-9]+)?"
PAKET = re.compile(r"paket/creator-profil-" + FASSUNG + r"\.zip")
MARKT = ".claude-plugin/marketplace.json"
PLUGIN = "ugc-werkstatt/.claude-plugin/plugin.json"
SKILL = "ugc-werkstatt/skills/creator-profil"
GPT = "gpt/creator-profil"
SKILL_ZIP = "skills/creator-profil.zip"
SAFE_ZONES = "werkzeug/safe-zones.html"
EINZELDATEIEN = {MARKT, PLUGIN, SKILL_ZIP, SAFE_ZONES, "fassungen.json"}
PROFILDATEI = re.compile(r"(?:[\w-]+/)*[\w-]+(?:\.[\w-]+)*\.(?:html|md|py|json|txt|png|jpg|jpeg|webp|svg)", re.ASCII)


class WerkstattRedirect(HTTPRedirectHandler):
    def redirect_request(self, req, fp, code, msg, headers, newurl):
        ziel = urlsplit(newurl)
        if (ziel.scheme != "https" or ziel.netloc not in {"marius-ugc.de", "www.marius-ugc.de"}
                or ziel.path != urlsplit(req.full_url).path or ziel.query or ziel.fragment):
            raise ValueError("Unerwartetes Weiterleitungsziel für die Werkstatt-Lieferung.")
        return super().redirect_request(req, fp, code, msg, headers, newurl)


def lade(url, ziel, grenze):
    with build_opener(WerkstattRedirect()).open(url, timeout=45) as antwort:
        daten = antwort.read(grenze + 1)
    if len(daten) > grenze:
        raise ValueError("Die Lieferung überschreitet die Größenbegrenzung.")
    ziel.write_bytes(daten)


def erlaubter_pfad(name):
    if name in EINZELDATEIEN or PAKET.fullmatch(name):
        return True
    for wurzel in (SKILL, GPT):
        if name.startswith(wurzel + "/") and PROFILDATEI.fullmatch(name[len(wurzel) + 1:]):
            return True
    return False


def pruefe_register(stufe, namen):
    register = json.loads((stufe / "fassungen.json").read_bytes())
    if not isinstance(register, list) or len(register) != 2:
        raise ValueError("Erwartet werden das Creator-Profil und Safe-Zones.")
    pakete = {p["kennung"]: p for p in register}
    if set(pakete) != {"creator-profil", "safe-zones"} or any(p["frei"] is not True for p in register):
        raise ValueError("Die Freigabeliste passt nicht zur Werkstatt.")
    profil, zonen = pakete["creator-profil"], pakete["safe-zones"]
    version = profil["fassung"]
    if not isinstance(version, str) or not re.fullmatch(FASSUNG, version):
        raise ValueError("Die Profilfassung ist ungültig.")
    paket = "paket/creator-profil-" + version + ".zip"
    if (profil["art"] != "ki" or profil["downloads"] != {"paket_zip": paket, "claude_zip": SKILL_ZIP, "gpt": GPT + "/"}
            or zonen["art"] != "werkzeug" or zonen["downloads"] != {}):
        raise ValueError("Die Produktarten oder Downloadziele weichen ab.")
    pflicht = EINZELDATEIEN | {paket, SKILL + "/SKILL.md", GPT + "/anweisung.md"}
    if not pflicht <= namen or {n for n in namen if PAKET.fullmatch(n)} != {paket}:
        raise ValueError("Das Archiv gehört nicht vollständig zur angegebenen Profilfassung.")
    markt = json.loads((stufe / MARKT).read_bytes())
    plugin = json.loads((stufe / PLUGIN).read_bytes())
    eintraege = markt.get("plugins", [])
    if (markt.get("name") != "ugc-werkstatt" or len(eintraege) != 1
            or eintraege[0].get("name") != "ugc-werkstatt" or eintraege[0].get("source") != "./ugc-werkstatt"
            or eintraege[0].get("version") != version or plugin.get("name") != "ugc-werkstatt"
            or plugin.get("version") != version or set(plugin) - {"name", "version", "description", "author"}
            or set(eintraege[0]) - {"name", "source", "version", "description"}):
        raise ValueError("Die Claude-Manifeste passen nicht zur Profilfassung.")
    return paket


def entpacke(archiv, summe, stufe):
    if (archiv.stat().st_size > MAX_ZIP or summe.stat().st_size > 200
            or not re.fullmatch(rb"[0-9a-f]{64} [ *]werkstatt-frei\.zip\r?\n?", summe.read_bytes())):
        raise ValueError("Archivgröße oder SHA-256-Datei ungültig.")
    if hashlib.sha256(archiv.read_bytes()).hexdigest() != summe.read_text("ascii")[:64]:
        raise ValueError("Die SHA-256-Prüfsumme stimmt nicht.")
    with ZipFile(archiv) as zipdatei:
        dateien = zipdatei.infolist()
        if len(dateien) > 2048 or sum(d.file_size for d in dateien) > MAX_INHALT:
            raise ValueError("Zu viele oder zu große Dateien im Gratisarchiv.")
        namen = set()
        for datei in dateien:
            name = datei.orig_filename
            if (name != datei.filename or name in namen or not erlaubter_pfad(name)
                    or stat.S_IFMT(datei.external_attr >> 16) not in (0, stat.S_IFREG)):
                raise ValueError("Unzulässiger oder doppelter Eintrag im Gratisarchiv.")
            namen.add(name)
            ziel = stufe / name
            ziel.parent.mkdir(parents=True, exist_ok=True)
            with zipdatei.open(datei) as quelle, ziel.open("xb") as ausgabe:
                shutil.copyfileobj(quelle, ausgabe)
    return pruefe_register(stufe, namen)


def uebernehme(archiv, summe, repo):
    repo = repo.resolve(strict=True)
    with tempfile.TemporaryDirectory(prefix="werkstatt-gratis-") as ort:
        stufe = Path(ort)
        paket = entpacke(archiv, summe, stufe)
        ziele = EINZELDATEIEN | {GPT, SKILL, paket}
        alt = repo / "paket"
        if alt.is_symlink():
            raise ValueError("Unerwarteter symbolischer Link im Zielpfad.")
        for datei in alt.glob("creator-profil-*.zip"):
            pfad = datei.relative_to(repo).as_posix()
            if PAKET.fullmatch(pfad):
                ziele.add(pfad)
        for name in ziele:
            ziel = repo / name
            if any(teil.is_symlink() for teil in [ziel, *ziel.parents] if teil.is_relative_to(repo)):
                raise ValueError("Unerwarteter symbolischer Link im Zielpfad.")
            if ziel.exists() and ziel.is_dir() != (name in {SKILL, GPT}):
                raise ValueError("Unerwarteter Datei- oder Ordnertyp im Ziel.")
        # Der Workflow veröffentlicht erst nach vollständiger Übernahme als einen Git-Commit.
        for name in sorted(ziele):
            ziel = repo / name
            quelle = stufe / name
            if ziel.is_dir():
                shutil.rmtree(ziel)
            elif ziel.exists():
                ziel.unlink()
            if quelle.exists():
                ziel.parent.mkdir(parents=True, exist_ok=True)
                if quelle.is_dir():
                    shutil.copytree(quelle, ziel)
                else:
                    shutil.copyfile(quelle, ziel)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("repo", type=Path)
    parser.add_argument("--archiv", type=Path)
    parser.add_argument("--sha256", type=Path)
    args = parser.parse_args()
    if bool(args.archiv) != bool(args.sha256):
        parser.error("--archiv und --sha256 gehören zusammen")
    with tempfile.TemporaryDirectory(prefix="werkstatt-lieferung-") as ort:
        archiv, summe = args.archiv, args.sha256
        if archiv is None:
            archiv, summe = Path(ort, "werkstatt-frei.zip"), Path(ort, "werkstatt-frei.zip.sha256")
            lade(QUELLE + ".sha256", summe, 200)
            lade(QUELLE, archiv, MAX_ZIP)
        uebernehme(archiv, summe, args.repo)
    print("Creator-Profil und Safe-Zones aus der geprüften Lieferung übernommen.")


if __name__ == "__main__":
    try:
        main()
    except (OSError, ValueError, KeyError, TypeError, BadZipFile) as fehler:
        sys.exit(f"Gratis-Spiegel fehlgeschlagen: {fehler}")
