# UGC-Werkstatt – Creator-Profil und Safe-Zones

Mit dem kostenlosen Creator-Profil richtest du Preise, Nische und Schreibstil für deine Werkstatt ein. Mit Safe-Zones prüfst du am Standbild, was eine App im Video verdeckt.

## Einrichten

- **ChatGPT oder Claude-Projekt** – Lade das versionierte ZIP aus `paket/`, entpacke es und öffne `Anleitung.html`.
- **Claude-App** – Lade `skills/creator-profil.zip` als Skill hoch.
- **Claude Code** – Gib `/plugin marketplace add Baccaraboy/ugc-werkstatt-frei` ein und installiere dann `ugc-werkstatt` von diesem Marktplatz.
- **Safe-Zones** – Lade `werkzeug/safe-zones.html` herunter und öffne die Datei im Browser.

## Veröffentlichung

Die GitHub Action „Freie Werkstatt aktualisieren“ lädt das Gratisarchiv und die zugehörige SHA-256-Datei von der [Werkstatt](https://marius-ugc.de/werkstatt). Sie prüft die Lieferung und aktualisiert die Produktdateien gemeinsam in einem Commit. In `fassungen.json` findest du die veröffentlichten Fassungen.

Nach einer Änderung am Workflow und alle sechs Stunden prüft die Action auf eine neue Lieferung. Über **Actions → Freie Werkstatt aktualisieren → Run workflow** kannst du sie auf `main` erneut starten. Bei einer unerreichbaren Quelle oder einer ungültigen Lieferung bleibt der zuletzt veröffentlichte Stand verfügbar. Die Action nutzt das GitHub-Token dieses Repos.
