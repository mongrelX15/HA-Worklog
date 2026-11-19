# HA-Worklog

[![Home Assistant](https://img.shields.io/badge/Home%20Assistant-Integration-41BDF5?logo=homeassistant&logoColor=white)](https://www.home-assistant.io/)
[![Status](https://img.shields.io/badge/status-Beta-orange)](#beta-0-1-0)

**HA Work-Log** erfasst Arbeitszeit-Signale und ordnet einen Tag erst nach einer konfigurierbaren Mindestdauer als Homeoffice- oder Bürotag ein. Unklare Standorte werden ausdrücklich als prüfbedürftig markiert.

## Beta 0.1.0

Die Home-Assistant-Custom-Integration wird über **Einstellungen → Geräte & Dienste → Integration hinzufügen → HA Work-Log** eingerichtet. Der Einrichtungsdialog ist auf Deutsch.

Bei der Einrichtung werden gewählt:

- eine Person-Entität (z. B. `person.marcel`)
- ein Binary-Sensor, der während der Arbeit aktiv ist (z. B. ein Ping-Sensor)
- optional die Bürozone
- Mindestarbeitszeit in Stunden (Standard: 2)

Die Integration erstellt die Sensoren **Arbeitszeit heute** und **Tagestyp** sowie den **Arbeitskalender**. Die Arbeitszeit zählt, solange Arbeitssignal und konfigurierte Personenzone gleichzeitig aktiv sind. Ein Bürotag wird erkannt, wenn die Person in der ausgewählten Bürozone ist; Zuhause wird als Homeoffice gewertet. Andere oder fehlende Standorte ergeben einen prüfbedürftigen Tag.

### Tageshistorie und Kalender

Der Arbeitskalender zeigt pro erfasstem Datum einen ganztägigen Eintrag mit Tagesart und Arbeitszeit. Er kann in Home Assistant über eine Kalenderkarte oder die Kalenderansicht angezeigt werden. Frühere Tage ab Installation dieser Beta bleiben lokal gespeichert und sind nach einem Neustart weiter verfügbar. Bereits vergangene Tage aus der Zeit vor diesem Update können nicht nachträglich rekonstruiert werden. Tage, an denen Home Assistant vollständig ausgeschaltet war, werden nicht als Arbeitszeit geschätzt.

Tageswerte werden lokal in Home Assistant gespeichert und beim Neustart wiederhergestellt. Bei Tageswechsel beginnt die Zählung neu. Diese Beta verwendet Zustandswechsel und eine Minutenaktualisierung; kurze Ausfälle können daher Messlücken verursachen. Das Ergebnis ist eine Orientierung und ersetzt keine verlässliche Zeiterfassung.

### Installation zum Testen

1. Installiere oder aktualisiere HA Work-Log aus dem Beta-Zweig.
2. Starte Home Assistant neu, falls es dazu auffordert.
3. Öffne **Einstellungen → Geräte & Dienste → HA Work-Log**. Dort sollte die Entität **Arbeitskalender** erscheinen.
4. Füge im Dashboard eine Kalenderkarte hinzu und wähle diese Kalender-Entität aus.

Wenn die Entität nach dem Update fehlt, lade die Integration neu oder starte Home Assistant neu. Frühere Tage werden erst ab dem Update aufgezeichnet.

Entfernen: Integration in Home Assistant löschen, danach den Ordner `custom_components/ha_worklog` entfernen und HA neu starten.

## Bekannte Grenzen dieser Beta

- Es gibt noch keine manuelle Tageskorrektur, Monats-/Jahresauswertung oder Exportfunktion.
- Die Messung kann höchstens die Qualität des konfigurierten Arbeitssignals erreichen; ein Ping-Sensor beweist keine tatsächliche Arbeitszeit.
- Ein Test in einer separaten HA-Testinstanz wird empfohlen.

## Projekt und Entwicklungsgrundsätze

HA Work-Log wird mit KI-Unterstützung entwickelt (Vibecoding). Anforderungen, fachliche Entscheidungen und Release-Freigaben liegen beim Projektverantwortlichen. KI unterstützt bei Planung, Architektur, Implementierung, Dokumentation und Tests.

Änderungen werden in Git versioniert und nachvollziehbar veröffentlicht. Der vorgesehene Ablauf ist, neue Änderungen zuerst im `beta`-Zweig zu erproben und geprüfte Änderungen anschließend in `main` als stabile Releases zu veröffentlichen.

Die GitHub-Actions-Pipeline prüft Python-Syntax und die vorhandenen Unit-Tests. Vor einer stabilen Freigabe sollen Änderungen zusätzlich vom Maintainer geprüft und in Home Assistant erprobt werden. Beta-Versionen können unvollständig sein oder Fehler enthalten.

## Entwicklung

Entwicklungszweig: `beta`. Stable liegt in `main` und wird durch diese Version nicht verändert. Die GitHub-Actions-Pipeline prüft Syntax und Unit-Tests.
