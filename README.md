# Steuertage

[![Home Assistant](https://img.shields.io/badge/Home%20Assistant-Integration-41BDF5?logo=homeassistant&logoColor=white)](https://www.home-assistant.io/)
[![Status](https://img.shields.io/badge/status-Beta-orange)](#installation-und-einrichtung)

**Steuertage** erfasst Tage mit Arbeitsstätte und Homeoffice für die Steuererklärung. Erfasste Zeit dient ausschließlich zur Berechnung, ob die Tagesschwelle erreicht wurde; im Kalender werden keine Arbeitsstunden angezeigt.

## Installation und Einrichtung

Die Integration wird unter **Einstellungen → Geräte & Dienste → Integration hinzufügen → Steuertage** eingerichtet. Alle Angaben werden in einem Dialog erfasst. Pro Person wird eine eigene Instanz angelegt:

- **Person**: Home-Assistant-Person
- **Arbeitsstätte (Zone)**: verpflichtend; gemeint ist der Ort, zu dem du für deine Arbeit fährst und dessen Besuche für Wegstrecken-Angaben relevant sein können. Die Zone dient der Anwesenheitserkennung.
- **Mindestanwesenheit**: erforderlich; bestimmt, wie lange ein Aufenthalt in einer relevanten Zone dauern muss, damit ein Tag automatisch zählt. Der Standardwert beträgt 2 Stunden; der Wert ist in 0,5-Stunden-Schritten einstellbar.
- **Homeoffice-Erkennung**: optional. Wenn aktiviert, sind Home-Zone und `device_tracker` erforderlich.
- **Arbeitskalender**: optional. Wenn aktiviert, muss ein in Home Assistant eingebundener Arbeitskalender ausgewählt werden.
- **Standardkalender**: wird anhand des angemeldeten Benutzers und der Benutzerzuordnung in der jeweiligen Home-Assistant-Person ausgewählt.

Ist Homeoffice aktiviert, zählt das Signal nur, wenn die Person und der ausgewählte Tracker beide in der eingestellten Home-Zone erkannt werden. Ein fehlender oder nicht verfügbarer Tracker wird nicht als Homeoffice gezählt. Bei deaktiviertem Homeoffice werden Home-Zone und Tracker in der Einrichtung ausgeblendet und sind nicht erforderlich; Homeoffice-Typen entfallen im Kalender und in der Auswertung. Dieser Anwesenheitsstatus ist kein Nachweis tatsächlicher Arbeitsleistung.

Ein Tag mit Arbeit vor Ort oder Homeoffice zählt, sobald das jeweilige Signal den pro Person eingestellten Schwellwert erreicht. Der Standard beträgt 2 Stunden. Wenn „Arbeitskalender verwenden“ aktiviert ist, zählt Arbeitszonenzeit nur während eines laufenden zeitgebundenen oder ganztägigen Arbeitstermins. So wird ein Aufenthalt an der Arbeitsadresse außerhalb einer eingetragenen Schicht nicht automatisch gewertet. Ohne Arbeitskalender bleibt die Erkennung über die Arbeitszone aktiv. Die Zeitmessung wird intern je Person getrennt geführt und erscheint nicht als Stundenübersicht.

## Mehrere Personen und Kalender

Jede Person erhält einen eigenen Kalender, Tagestyp-Sensor und getrennten lokalen Verlauf. Der Homeoffice-Sensor wird nur angelegt, wenn Homeoffice für diese Person aktiviert ist. Derselbe Arbeits- oder Home-Zonenbereich kann von mehreren Personen verwendet werden; eine Person und ein Homeoffice-Gerät können jeweils nur einer Konfiguration zugeordnet sein.

Das Panel **Steuertage** wird einmalig in der Seitenleiste angelegt. Es ermöglicht allen angemeldeten Benutzern den Wechsel zwischen eingerichteten Kalendern und manuelle Korrekturen. Home Assistant wählt den Kalender der Person, die mit dem angemeldeten Benutzer verknüpft ist, als Standardansicht; Kalender-Tabs bleiben verfügbar. Verknüpfe Benutzer und Person dazu in den Home-Assistant-Personeneinstellungen.

Manuelle Korrekturen werden der betroffenen Person und dem angemeldeten HA-Benutzer zugeordnet. Die Historie speichert Zeitpunkt sowie alten und neuen Status. Ein übergebener Benutzername wird nicht als Identität verwendet.

## Kalender und Panel

Der Kalender zeigt Tagesstatus, Wochenenden, Monatsstatistik und dezente Hinweise auf manuell geänderte Tage. Manuelle Korrekturen lassen sich auf einen einzelnen Tag oder einen Zeitraum bis zu 366 Tagen anwenden. Das Panel übernimmt die aktiven Theme-Farben und den Hell-/Dunkelmodus von Home Assistant. Der **Konfigurator** zeigt die Personeneinstellungen, prüft benötigte Entitäten und führt direkt zu den Home-Assistant-Optionen. Er erklärt die automatische Erkennung, den optionalen Arbeitskalender und den pro Person einstellbaren Schwellwert (Standard 2 Stunden). Der **Export** erlaubt einen Jahres- oder frei gewählten Zeitraum und erstellt CSV-, TXT- und HTML-Dateien mit Gesamtsummen, Monatsübersicht, Tagesliste und Prüfliste für ungeklärte oder noch laufende Erkennung. „Arbeit vor Ort + Homeoffice“ wird als eigene Kategorie und als ein Arbeitstag gezählt. Eine JSON-Sicherung enthält die Verläufe aller in Steuertage eingerichteten Personen. Beim Wiederherstellen kannst du fehlende Tage ergänzen und neuere lokale Änderungen behalten oder die gesicherten Einträge der enthaltenen Tage ersetzen. Tage, die nicht in der Sicherung stehen, bleiben erhalten. Sicherung und Wiederherstellung erfordern einen Home-Assistant-Administrator. Die Auswertung berücksichtigt nur Tage, die von Steuertage erfasst wurden. Steuertage unterstützt die automatische Erfassung relevanter Daten auf Grundlage der in Home Assistant vorhandenen Erkennung; für Richtigkeit und Vollständigkeit der Steuererklärung ist der Nutzer selbst verantwortlich. Angaben ohne Gewähr.

## Hinweis zum Umstieg von HA Work-Log

Diese Version verwendet die neue Integrations-Domain `steuertage` und den Ordner `custom_components/steuertage`. Sie ist daher ein Neustart und kein direktes Upgrade der bisherigen `ha_worklog`-Integration. Entferne die alte HA Work-Log-Integration in Home Assistant und sichere benötigte Daten vorher separat. Anschließend installierst du Steuertage neu und richtest die Personen erneut ein. Alte Konfigurationen und lokale Verläufe werden nicht automatisch übernommen.

## Homeoffice-Konfigurationen aus älteren Betas

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


## Versionshinweise

Änderungen je Version findest du in den [GitHub Release Notes](https://github.com/mongrelX15/Steuertage/releases).
