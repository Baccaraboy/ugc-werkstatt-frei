import hashlib
import json
from pathlib import Path
import tempfile
import unittest
from zipfile import ZipFile

from gratis_spiegel import GPT, MARKT, PLUGIN, SAFE_ZONES, SKILL, SKILL_ZIP, uebernehme


class GratisSpiegelTest(unittest.TestCase):
    def setUp(self):
        ort = tempfile.TemporaryDirectory()
        self.addCleanup(ort.cleanup)
        self.root = Path(ort.name)
        self.repo = self.root / "repo"
        self.repo.mkdir()
        self.paket = "paket/creator-profil-1.2.zip"
        self.profil = {"kennung": "creator-profil", "art": "ki", "frei": True, "fassung": "1.2",
                       "downloads": {"paket_zip": self.paket, "claude_zip": SKILL_ZIP, "gpt": GPT + "/"}}
        self.zonen = {"kennung": "safe-zones", "art": "werkzeug", "frei": True, "downloads": {}}
        self.markt = {"name": "ugc-werkstatt", "plugins": [{"name": "ugc-werkstatt", "source": "./ugc-werkstatt", "version": "1.2"}]}
        self.dateien = {self.paket: b"Profilpaket", SKILL_ZIP: b"Profilskill", SAFE_ZONES: b"Safe-Zones",
                        SKILL + "/SKILL.md": b"Skill", GPT + "/anweisung.md": b"Anweisung",
                        PLUGIN: json.dumps({"name": "ugc-werkstatt", "version": "1.2"})}
        self.archiv = self.root / "werkstatt-frei.zip"
        self.summe = self.root / "werkstatt-frei.zip.sha256"

    def baue(self):
        with ZipFile(self.archiv, "w") as z:
            for name, inhalt in self.dateien.items():
                z.writestr(name, inhalt)
            z.writestr("fassungen.json", json.dumps([self.profil, self.zonen]))
            z.writestr(MARKT, json.dumps(self.markt))
        self.summe.write_text(hashlib.sha256(self.archiv.read_bytes()).hexdigest() + "  werkstatt-frei.zip\n")

    def uebernehmen(self):
        uebernehme(self.archiv, self.summe, self.repo)

    def test_ersetzen_und_wiederholen(self):
        (self.repo / "paket").mkdir()
        (self.repo / "paket/creator-profil-1.1.zip").write_text("alt")
        behalten = self.repo / "paket/eigene-notiz.txt"
        behalten.write_text("behalten")
        self.baue()
        self.uebernehmen()
        self.uebernehmen()
        self.assertFalse((self.repo / "paket/creator-profil-1.1.zip").exists())
        self.assertEqual((self.repo / self.paket).read_bytes(), b"Profilpaket")
        self.assertEqual(behalten.read_text(), "behalten")

    def test_summenfehler_lasst_alten_stand_stehen(self):
        self.baue()
        self.uebernehmen()
        self.archiv.write_bytes(b"unvollstaendig")
        with self.assertRaisesRegex(ValueError, "Prüfsumme"):
            self.uebernehmen()
        self.assertEqual((self.repo / self.paket).read_bytes(), b"Profilpaket")

    def test_fremdes_produkt_und_falscher_download(self):
        self.profil["frei"] = False
        self.baue()
        with self.assertRaisesRegex(ValueError, "Freigabeliste"):
            self.uebernehmen()
        self.profil["frei"] = True
        self.profil["downloads"]["paket_zip"] = "paket/andere.zip"
        self.baue()
        with self.assertRaisesRegex(ValueError, "Downloadziele"):
            self.uebernehmen()

    def test_nur_produktpfade(self):
        for name in ("paket/buero-autopilot-1.0.zip", ".github/workflows/extra.yml",
                     "gpt/anderes/anweisung.md", GPT + "/../datei.md", SKILL + "/.claude/settings.json"):
            with self.subTest(name=name):
                self.dateien[name] = b"x"
                self.baue()
                with self.assertRaisesRegex(ValueError, "Eintrag"):
                    self.uebernehmen()
                del self.dateien[name]
        self.assertEqual(list(self.repo.iterdir()), [])

    def test_keine_weiteren_claude_quellen(self):
        self.markt["plugins"][0]["source"] = "https://example.invalid/plugin"
        self.baue()
        with self.assertRaisesRegex(ValueError, "Claude-Manifeste"):
            self.uebernehmen()

    def test_fehlender_download(self):
        del self.dateien[SKILL_ZIP]
        self.baue()
        with self.assertRaisesRegex(ValueError, "vollständig"):
            self.uebernehmen()

    def test_links_im_ziel(self):
        (self.repo / "gpt").symlink_to(self.root, target_is_directory=True)
        self.baue()
        with self.assertRaisesRegex(ValueError, "symbolischer Link"):
            self.uebernehmen()
        self.assertFalse((self.root / "creator-profil").exists())


if __name__ == "__main__":
    unittest.main()
