# HA-Worklog

[![Home Assistant](https://img.shields.io/badge/Home%20Assistant-Integration-41BDF5?logo=homeassistant&logoColor=white)](https://www.home-assistant.io/)
[![Status](https://img.shields.io/badge/status-Beta-orange)](#beta-0-1-0)

**HA Work-Log** erkennt steuerlich relevante Arbeitstage aus einer Arbeitszone und einem Homeoffice-Sensor. Die Erkennungsdauer dient nur als Schwellwert; sie wird nicht im Arbeitskalender angezeigt.

## Beta 0.1.0

Die Home-Assistant-Custom-Integration wird über **Einstellungen → Geräte & Dienste → Integration hinzufügen → HA Work-Log** eingerichtet. Der Einrichtungsdialog ist auf Deutsch.

Bei der Einrichtung werden gewählt:

- eine Person-Entität
- ein Binary-Sensor für das Homeoffice
- optional eine Arbeitszone für Bürotage

Ein Tag zählt in dieser Beta, sobald der Homeoffice-Sensor oder die Arbeitszone mindestens 30 Minuten aktiv war. Wenn beide Signale die Schwelle erreichen, zählt es weiterhin als ein Kalendertag; der Eintrag kennzeichnet beide Signale. Homeoffice- und Arbeitszonenzeiten werden getrennt intern ausgewertet. Die Dauer wird nicht in der Kalenderübersicht angezeigt.

Die Integration stellt einen **Arbeitskalender** und den Sensor **Tagestyp** bereit. Der Kalender speichert die Tagesergebnisse lokal in Home Assistant und zeigt sie als ganztägige Einträge. Die Historie beginnt mit dieser Beta und bleibt nach einem Neustart erhalten. Bereits vergangene Tage vor dem Update können nicht rekonstruiert werden.

### Dashboard

In Home Assistant gibt es ein separates Dashboard **HA Work-Log** mit den Reitern **Kalender**, **Konfigurator** und **Export**. Die Ansichten verwenden HA-Standardelemente und folgen daher dem aktiven Theme und Dark Mode.

Der Kalender zeigt die automatische Tageserkennung. Manuelle Korrektur, farbliche Tageskategorien und die vollständigen Konfigurator-Eingaben werden schrittweise ergänzt. Der Export-Reiter ist derzeit nur vorbereitet und enthält noch keine Exportfunktion.

### Installation zum Testen

1. Aktualisiere HA Work-Log über HACS auf die Beta-Version.
2. Starte Home Assistant neu oder lade die Integration neu.
3. Öffne das Dashboard **HA Work-Log** in der Seitenleiste.
4. Prüfe, ob der Arbeitskalender Tagesergebnisse ohne Stundenangabe zeigt.

Entfernen: Integration in Home Assistant löschen, danach den Ordner `custom_components/ha_worklog` entfernen und HA neu starten.

## Projekt und Entwicklungsgrundsätze

HA Work-Log wird mit KI-Unterstützung entwickelt (Vibecoding). Anforderungen und fachliche Entscheidungen kommen vom Projektverantwortlichen. Änderungen werden in Git zunächst im `beta`-Zweig erprobt; geprüfte Änderungen werden später als stabile Version in `main` veröffentlicht.

Beta-Versionen können unvollständig sein oder Fehler enthalten. Ein Test in einer separaten HA-Testinstanz wird empfohlen.
