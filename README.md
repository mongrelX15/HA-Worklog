# Steuertage

[![Home Assistant](https://img.shields.io/badge/Home%20Assistant-Integration-41BDF5?logo=homeassistant&logoColor=white)](https://www.home-assistant.io/)
[![Status](https://img.shields.io/badge/status-Stable-brightgreen)](#version-010)

**Büro- und Homeoffice-Tage für die Steuererklärung**

Steuertage erfasst und wertet steuerlich relevante Arbeitstage aus. Die Zeit wird nur intern verwendet, um die Tagesschwelle zu berechnen; die App ist keine Arbeitszeiterfassung und zeigt keine Stundenübersicht.

## Version 0.1.0

Pro Person wird eine eigene Instanz unter **Einstellungen → Geräte & Dienste → Integration hinzufügen → Steuertage** eingerichtet:

- **Person**: Home-Assistant-Person
- **Home-Zone**: standardmäßig `zone.home`
- **Homeoffice-Gerät**: `device_tracker`, der Homeoffice-Anwesenheit signalisiert
- **Büro-Zone**: optional
- **HA-Benutzer**: optionaler Standardkalender beim Öffnen

Ein Homeoffice-Tag zählt, wenn die Person und das ausgewählte Gerät beide mindestens 30 Minuten in der Home-Zone erkannt wurden. Ein nicht verfügbarer Tracker wird nicht als bestätigtes Homeoffice gewertet. Der zugehörige Binary-Sensor zeigt Erkennungsstatus und Diagnoseattribute. Anwesenheit ist kein Nachweis tatsächlicher Arbeitsleistung.

Ein Bürotag zählt, wenn die Person mindestens 30 Minuten in der konfigurierten Büro-Zone erkannt wurde. Die Schwelle beträgt in Version 0.1.0 fest 30 Minuten.

## Mehrere Personen

Jede Person erhält eigene Sensoren, einen Kalender, getrennte Erkennungszeiten, Verlauf und manuelle Korrekturen. Eine Person und ein Homeoffice-Gerät können jeweils nur einer Instanz zugeordnet sein; gemeinsame Zonen sind möglich.

Das Seitenleisten-Panel **Steuertage** zeigt den Kalender des angemeldeten HA-Benutzers als Startansicht. Bei mehreren eingerichteten Personen erscheinen Tabs zum Wechseln zwischen allen Work-Logs. Ohne zusätzliche Person blendet das Panel die Tab-Auswahl aus.

Manuelle Korrekturen speichern die betroffene Person, den angemeldeten HA-Benutzer, den Zeitpunkt, alten und neuen Tagesstatus und optional einen Änderungsgrund. Das Panel folgt dem aktiven Home-Assistant-Theme und markiert manuelle Korrekturen dezent.

Der **Konfigurator** führt zu den Einstellungen der Integration. Der **Export**-Reiter ist vorbereitet, bietet in Version 0.1.0 aber noch keine Exportfunktion.

## Wichtiger Hinweis zum Umstieg von HA Work-Log

Steuertage verwendet die neue technische Integrations-Domain `steuertage` statt `ha_worklog`. Das ist kein automatisches Upgrade: Bestehende HA Work-Log-Konfigurationen, Entity-IDs und lokale Verläufe werden nicht übernommen.

Wenn du alte Daten behalten möchtest, sichere oder exportiere sie vor dem Umstieg. Entferne anschließend die alte HA Work-Log-Integration, aktualisiere die Dateien über HACS/Marketplace, starte Home Assistant neu und füge **Steuertage** hinzu. Personen und Sensoren müssen neu eingerichtet werden.

## Installation

1. Installiere Version **0.1.0** über HACS/Marketplace.
2. Starte Home Assistant neu.
3. Füge unter **Einstellungen → Geräte & Dienste** die Integration **Steuertage** hinzu.
4. Richte jede Person ein und ordne bei Bedarf den passenden HA-Benutzer zu.

Für manuelle Installation kopiere `custom_components/steuertage` nach `<config>/custom_components/steuertage` und starte Home Assistant neu.

## Projekt und Entwicklungsgrundsätze

Steuertage wird mit KI-Unterstützung entwickelt. Fachliche Anforderungen und Entscheidungen kommen vom Projektverantwortlichen; Änderungen werden in Git geprüft und versioniert. Der `beta`-Zweig dient der Erprobung; geprüfte Stände werden als stabile Version in `main` veröffentlicht.
