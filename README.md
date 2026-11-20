# Steuertage

[![Home Assistant](https://img.shields.io/badge/Home%20Assistant-Integration-41BDF5?logo=homeassistant&logoColor=white)](https://www.home-assistant.io/)
[![Status](https://img.shields.io/badge/status-Beta-orange)](#beta-0-2-0-beta-1)

**Steuertage** erfasst Büro- und Homeoffice-Tage für die Steuererklärung. Erfasste Zeit dient ausschließlich zur Berechnung, ob die Tagesschwelle erreicht wurde; im Kalender werden keine Arbeitsstunden angezeigt.

## Beta 0.2.0-beta.1 – Konfigurator und Jahres-Export

Die Integration wird unter **Einstellungen → Geräte & Dienste → Integration hinzufügen → Steuertage** eingerichtet. Pro Person wird eine eigene Instanz angelegt:

- **Person**: Home-Assistant-Person
- **Home-Zone**: standardmäßig `zone.home`
- **Homeoffice-Gerät**: `device_tracker` des Geräts, das Homeoffice-Anwesenheit signalisiert
- **Büro-Zone**: optional
- **HA-Benutzer**: optionaler Standardkalender beim Öffnen des Panels

Ein Homeoffice-Signal gilt nur, wenn die Person und das ausgewählte Gerät beide in der eingestellten Home-Zone erkannt werden. Ein fehlender oder nicht verfügbarer Tracker wird nicht als Homeoffice gezählt. Die Integration stellt dafür pro Person einen Homeoffice-Binary-Sensor mit Status- und Diagnoseattributen bereit. Dieser Anwesenheitsstatus ist kein Nachweis tatsächlicher Arbeitsleistung.

Ein Arbeitstag zählt, wenn die konfigurierte Büro-Zone oder die Homeoffice-Erkennung mindestens 30 Minuten aktiv war. Die Zeitmessung wird intern je Person getrennt geführt und erscheint nicht als Stundenübersicht.

## Mehrere Personen und Kalender

Jede Person erhält einen eigenen Kalender, Tagestyp-Sensor, Homeoffice-Sensor und getrennten lokalen Verlauf. Derselbe Büro- oder Home-Zonenbereich kann von mehreren Personen verwendet werden; eine Person und ein Homeoffice-Gerät können jeweils nur einer Konfiguration zugeordnet sein.

Das Panel **Steuertage** wird einmalig in der Seitenleiste angelegt. Es ermöglicht allen angemeldeten Benutzern den Wechsel zwischen eingerichteten Kalendern und manuelle Korrekturen. Ist einer Person ein HA-Benutzer zugeordnet, öffnet sich dessen Kalender standardmäßig; die Auswahl bleibt jederzeit veränderbar.

Manuelle Korrekturen werden der betroffenen Person und dem angemeldeten HA-Benutzer zugeordnet. Die Historie speichert Zeitpunkt sowie alten und neuen Status. Ein übergebener Benutzername wird nicht als Identität verwendet.

## Kalender und Panel

Der Kalender zeigt Tagesstatus, Wochenenden, Monatsstatistik und dezente Hinweise auf manuell geänderte Tage. Das Theme des Home-Assistant-Benutzers wird übernommen. Der **Konfigurator** zeigt Person, Home- und Büro-Zone, Tracker und Benutzerzuordnung je Einrichtung an und führt direkt zu den Home-Assistant-Optionen. Er erklärt die automatische Erkennung und den festen Beta-Schwellwert von 30 Minuten. Der **Export** erstellt CSV-, TXT- und HTML-Dateien mit Jahresstatistik, Tagesliste und Hinweisen für ungeklärte oder noch laufende Erkennung. „Büro + Homeoffice“ wird als eigene Kategorie und als ein Arbeitstag gezählt.

## Hinweis zum Umstieg von HA Work-Log

Diese Version verwendet die neue Integrations-Domain `steuertage` und den Ordner `custom_components/steuertage`. Sie ist daher ein Neustart und kein direktes Upgrade der bisherigen `ha_worklog`-Integration. Entferne die alte HA Work-Log-Integration in Home Assistant und sichere benötigte Daten vorher separat. Anschließend installierst du Steuertage neu und richtest die Personen erneut ein. Alte Konfigurationen und lokale Verläufe werden nicht automatisch übernommen.

## Bestehende Beta-7-Konfigurationen

Beim Upgrade bleibt die bestehende Konfiguration und der lokale Verlauf unter derselben Integrations-ID erhalten. Ältere Einträge können in den Optionen zunächst weiterhin den bisherigen Homeoffice-Binary-Sensor nutzen. Für die neue Erkennung kann ein `device_tracker` ausgewählt werden; danach wird der bisherige Sensor nicht mehr für die automatische Erkennung verwendet.

Bei der Umstellung werden frühere Datensätze nach Möglichkeit übernommen. Vergangene Tage, die vor der ersten Erfassung nicht gespeichert wurden, lassen sich nicht nachträglich rekonstruieren.

## Installation und Test

1. Installiere die Beta über HACS oder den Beta-Zweig des Repositories.
2. Starte Home Assistant neu oder lade Steuertage neu.
3. Öffne **Einstellungen → Geräte & Dienste → Steuertage** und prüfe die Personeneinstellungen und neuen Entitäten.
4. Füge eine weitere Person über **Integration hinzufügen → Steuertage** hinzu und öffne anschließend das Seitenleisten-Panel.

Entfernen: Integration in Home Assistant löschen, danach den Ordner `custom_components/steuertage` entfernen und Home Assistant neu starten.

## Projekt und Entwicklungsgrundsätze

Steuertage wird mit KI-Unterstützung entwickelt (Vibecoding). Anforderungen und fachliche Entscheidungen kommen vom Projektverantwortlichen. Änderungen werden in Git zunächst im `beta`-Zweig erprobt; geprüfte Änderungen werden später als stabile Version in `main` veröffentlicht.

Beta-Versionen können unvollständig sein oder Fehler enthalten. Ein Test in einer separaten Home-Assistant-Testinstanz wird empfohlen.
