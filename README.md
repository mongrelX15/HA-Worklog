# Steuertage

[![Home Assistant](https://img.shields.io/badge/Home%20Assistant-Integration-41BDF5?logo=homeassistant&logoColor=white)](https://www.home-assistant.io/)
[![Status](https://img.shields.io/badge/status-Beta-orange)](#beta-0-2-0-beta-3-optionale-homeoffice-erkennung-arbeitskalender-und-schwellenwert)

**Steuertage** erfasst Büro- und Homeoffice-Tage für die Steuererklärung. Erfasste Zeit dient ausschließlich zur Berechnung, ob die Tagesschwelle erreicht wurde; im Kalender werden keine Arbeitsstunden angezeigt.

## Beta 0.2.0-beta.3 – optionale Homeoffice-Erkennung, Arbeitskalender und Schwellenwert

Die Integration wird unter **Einstellungen → Geräte & Dienste → Integration hinzufügen → Steuertage** eingerichtet. Pro Person wird eine eigene Instanz angelegt:

- **Person**: Home-Assistant-Person
- **Homeoffice-Erkennung**: optional; wenn aktiviert, wird eine Home-Zone und ein `device_tracker` benötigt
- **Büro-Zone**: optional; in dieser Zone wird ein Bürotag erkannt
- **Arbeitskalender**: optional; begrenzt die Büro-Erkennung auf laufende zeitgebundene Schichten. Ganztägige Kalendereinträge zählen nicht. Ohne Auswahl gilt reine Zonenerkennung.
- **Schwellwert**: frei einstellbar in Minuten, Standardwert 120 Minuten
- **HA-Benutzer**: optionaler Standardkalender beim Öffnen des Panels

Ist Homeoffice aktiviert, zählt das Signal nur, wenn die Person und der ausgewählte Tracker beide in der eingestellten Home-Zone erkannt werden. Ein fehlender oder nicht verfügbarer Tracker wird nicht als Homeoffice gezählt. Bei deaktiviertem Homeoffice sind weder Tracker noch Home-Zone erforderlich; die entsprechenden Auswahlmöglichkeiten entfallen im Kalender und in der Auswertung. Dieser Anwesenheitsstatus ist kein Nachweis tatsächlicher Arbeitsleistung.

Ein Büro- oder Homeoffice-Tag zählt, sobald das jeweilige Signal den pro Person eingestellten Schwellwert erreicht. Der Standard beträgt 120 Minuten. Ein optional ausgewählter Arbeitskalender lässt Bürozeit nur während eines laufenden zeitgebundenen Eintrags zählen. So wird ein Aufenthalt an der Arbeitsadresse außerhalb einer eingetragenen Schicht nicht automatisch gewertet. Ohne Arbeitskalender bleibt die bisherige Erkennung über die Büro-Zone aktiv. Die Zeitmessung wird intern je Person getrennt geführt und erscheint nicht als Stundenübersicht.

## Mehrere Personen und Kalender

Jede Person erhält einen eigenen Kalender, Tagestyp-Sensor und getrennten lokalen Verlauf. Der Homeoffice-Sensor wird nur angelegt, wenn Homeoffice für diese Person aktiviert ist. Derselbe Büro- oder Home-Zonenbereich kann von mehreren Personen verwendet werden; eine Person und ein Homeoffice-Gerät können jeweils nur einer Konfiguration zugeordnet sein.

Das Panel **Steuertage** wird einmalig in der Seitenleiste angelegt. Es ermöglicht allen angemeldeten Benutzern den Wechsel zwischen eingerichteten Kalendern und manuelle Korrekturen. Ist einer Person ein HA-Benutzer zugeordnet, öffnet sich dessen Kalender standardmäßig; die Auswahl bleibt jederzeit veränderbar.

Manuelle Korrekturen werden der betroffenen Person und dem angemeldeten HA-Benutzer zugeordnet. Die Historie speichert Zeitpunkt sowie alten und neuen Status. Ein übergebener Benutzername wird nicht als Identität verwendet.

## Kalender und Panel

Der Kalender zeigt Tagesstatus, Wochenenden, Monatsstatistik und dezente Hinweise auf manuell geänderte Tage. Manuelle Korrekturen lassen sich auf einen einzelnen Tag oder einen Zeitraum bis zu 366 Tagen anwenden. Das Panel übernimmt die aktiven Theme-Farben und den Hell-/Dunkelmodus von Home Assistant. Der **Konfigurator** zeigt die Personeneinstellungen, prüft benötigte Entitäten und führt direkt zu den Home-Assistant-Optionen. Er erklärt die automatische Erkennung, den optionalen Arbeitskalender und den pro Person einstellbaren Schwellwert (Standard 120 Minuten). Der **Export** erlaubt einen Jahres- oder frei gewählten Zeitraum und erstellt CSV-, TXT- und HTML-Dateien mit Gesamtsummen, Monatsübersicht, Tagesliste und Prüfliste für ungeklärte oder noch laufende Erkennung. „Büro + Homeoffice“ wird als eigene Kategorie und als ein Arbeitstag gezählt. Eine JSON-Sicherung enthält den Verlauf der ausgewählten Person. Wiederherstellen ergänzt nur fehlende Datumswerte; vorhandene Tage werden beibehalten. Sicherung und Wiederherstellung erfordern einen Home-Assistant-Administrator. Die Auswertung berücksichtigt nur Tage, die von Steuertage erfasst wurden. Steuertage unterstützt die automatische Erfassung relevanter Daten auf Grundlage der in Home Assistant vorhandenen Erkennung; für Richtigkeit und Vollständigkeit der Steuererklärung ist der Nutzer selbst verantwortlich. Angaben ohne Gewähr.

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
