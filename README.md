# Steuertage

[![Home Assistant](https://img.shields.io/badge/Home%20Assistant-Integration-41BDF5?logo=homeassistant&logoColor=white)](https://www.home-assistant.io/)
[![Status](https://img.shields.io/badge/status-Beta-orange)](#beta-0-2-0-beta-4-kalender-export-und-wiederherstellung)

**Steuertage** erfasst Tage mit Arbeit vor Ort und Homeoffice für die Steuererklärung. Erfasste Zeit dient ausschließlich zur Berechnung, ob die Tagesschwelle erreicht wurde; im Kalender werden keine Arbeitsstunden angezeigt.

## Beta 0.2.0-beta.6 – Theme und überarbeitete Ansichten

Die Integration wird unter **Einstellungen → Geräte & Dienste → Integration hinzufügen → Steuertage** eingerichtet. Pro Person wird eine eigene Instanz angelegt:

- **Person**: Home-Assistant-Person
- **Homeoffice-Erkennung**: optional; wenn aktiviert, wird eine Home-Zone und ein `device_tracker` benötigt
- **Arbeitszone (Standort der Arbeit)**: verpflichtend; in dieser Zone wird ein Arbeitstag vor Ort erkannt
- **Arbeitskalender verwenden (Ja/Nein)**: optional; bei Ja wählst du im nächsten Schritt einen in Home Assistant eingebundenen Kalender. Er begrenzt die Erkennung auf laufende zeitgebundene oder ganztägige Arbeitstermine. Bei Nein gilt reine Zonenerkennung.
- **Schwellwert**: frei einstellbar in Stunden (0,5-Stunden-Schritte), Standardwert 2 Stunden
- **Standardkalender**: wird automatisch anhand des angemeldeten Benutzers und der Benutzerzuordnung in der jeweiligen Home-Assistant-Person ausgewählt

Ist Homeoffice aktiviert, zählt das Signal nur, wenn die Person und der ausgewählte Tracker beide in der eingestellten Home-Zone erkannt werden. Ein fehlender oder nicht verfügbarer Tracker wird nicht als Homeoffice gezählt. Bei deaktiviertem Homeoffice werden Home-Zone und Tracker in der Einrichtung ausgeblendet und sind nicht erforderlich; Homeoffice-Typen entfallen im Kalender und in der Auswertung. Dieser Anwesenheitsstatus ist kein Nachweis tatsächlicher Arbeitsleistung.

Ein Tag mit Arbeit vor Ort oder Homeoffice zählt, sobald das jeweilige Signal den pro Person eingestellten Schwellwert erreicht. Der Standard beträgt 2 Stunden. Wenn „Arbeitskalender verwenden“ aktiviert ist, zählt Arbeitszonenzeit nur während eines laufenden zeitgebundenen oder ganztägigen Arbeitstermins. So wird ein Aufenthalt an der Arbeitsadresse außerhalb einer eingetragenen Schicht nicht automatisch gewertet. Ohne Arbeitskalender bleibt die Erkennung über die Arbeitszone aktiv. Die Zeitmessung wird intern je Person getrennt geführt und erscheint nicht als Stundenübersicht.

## Mehrere Personen und Kalender

Jede Person erhält einen eigenen Kalender, Tagestyp-Sensor und getrennten lokalen Verlauf. Der Homeoffice-Sensor wird nur angelegt, wenn Homeoffice für diese Person aktiviert ist. Derselbe Arbeits- oder Home-Zonenbereich kann von mehreren Personen verwendet werden; eine Person und ein Homeoffice-Gerät können jeweils nur einer Konfiguration zugeordnet sein.

Das Panel **Steuertage** wird einmalig in der Seitenleiste angelegt. Es ermöglicht allen angemeldeten Benutzern den Wechsel zwischen eingerichteten Kalendern und manuelle Korrekturen. Home Assistant wählt den Kalender der Person, die mit dem angemeldeten Benutzer verknüpft ist, als Standardansicht; Kalender-Tabs bleiben verfügbar. Verknüpfe Benutzer und Person dazu in den Home-Assistant-Personeneinstellungen.

Manuelle Korrekturen werden der betroffenen Person und dem angemeldeten HA-Benutzer zugeordnet. Die Historie speichert Zeitpunkt sowie alten und neuen Status. Ein übergebener Benutzername wird nicht als Identität verwendet.

## Kalender und Panel

Der Kalender zeigt Tagesstatus, Wochenenden, Monatsstatistik und dezente Hinweise auf manuell geänderte Tage. Manuelle Korrekturen lassen sich auf einen einzelnen Tag oder einen Zeitraum bis zu 366 Tagen anwenden. Das Panel übernimmt die aktiven Theme-Farben und den Hell-/Dunkelmodus von Home Assistant. Der **Konfigurator** zeigt die Personeneinstellungen, prüft benötigte Entitäten und führt direkt zu den Home-Assistant-Optionen. Er erklärt die automatische Erkennung, den optionalen Arbeitskalender und den pro Person einstellbaren Schwellwert (Standard 2 Stunden). Der **Export** erlaubt einen Jahres- oder frei gewählten Zeitraum und erstellt CSV-, TXT- und HTML-Dateien mit Gesamtsummen, Monatsübersicht, Tagesliste und Prüfliste für ungeklärte oder noch laufende Erkennung. „Arbeit vor Ort + Homeoffice“ wird als eigene Kategorie und als ein Arbeitstag gezählt. Eine JSON-Sicherung enthält den Verlauf der ausgewählten Person. Beim Wiederherstellen kannst du fehlende Tage ergänzen und neuere lokale Änderungen behalten oder die gesicherten Einträge der enthaltenen Tage ersetzen. Tage, die nicht in der Sicherung stehen, bleiben erhalten. Sicherung und Wiederherstellung erfordern einen Home-Assistant-Administrator. Die Auswertung berücksichtigt nur Tage, die von Steuertage erfasst wurden. Steuertage unterstützt die automatische Erfassung relevanter Daten auf Grundlage der in Home Assistant vorhandenen Erkennung; für Richtigkeit und Vollständigkeit der Steuererklärung ist der Nutzer selbst verantwortlich. Angaben ohne Gewähr.

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


### Änderungen in Beta 0.2.0-beta.6

- Der Kalender richtet sich nach der Spracheinstellung von Home Assistant und zeigt Datumsangaben lokalisiert an.
- Tagestypen sind in der Kalenderauswahl klar hervorgehoben. Tage lassen sich durch Ziehen über den Kalender als Zeitraum auswählen und gemeinsam ändern.
- Die Bezeichnung „Bürotag“ wurde durch „Arbeit vor Ort“ ersetzt.
- Im Export gibt es Schnellwahl für die Steuerjahre, den aktuellen Monat und die aktuelle Woche. Die Prüfliste steht über den Zeitraumfiltern.
- Sicherungen können fehlende Tage ergänzen und lokale Änderungen nach dem Sicherungszeitpunkt bewahren oder gesicherte Einträge für enthaltene Tage ersetzen. Nicht enthaltene Tage bleiben erhalten.
- Die Panel-Registrierung wird beim Neuladen der Integration aktualisiert, damit Home Assistant das neue JavaScript nach einem HACS-Update verwendet.
- Das Panel liest die aktiven Home-Assistant-Themefarben gezielt aus dem CSS-Kontext sowie aus den ausgewählten Theme-Einstellungen und nutzt passende helle/dunkle Rückfallfarben.
- Konfiguration und Export haben eine klarere Gliederung, kompakte Einstellungs-Kacheln und eine besser erkennbare Zeitraum-Auswahl erhalten.
