# HA-Worklog

[![Home Assistant](https://img.shields.io/badge/Home%20Assistant-Integration-41BDF5?logo=homeassistant&logoColor=white)](https://www.home-assistant.io/)
[![Status](https://img.shields.io/badge/status-in%20development-orange)](#projektstatus)

**HA-Worklog** ist ein Home-Assistant-Projekt zur automatisierten und nachvollziehbaren Erfassung von Arbeitstagen und Homeoffice-Tagen. Es soll Arbeitszeiten und Aufenthaltsinformationen aus vorhandenen Home-Assistant-Entitäten zusammenführen und daraus belastbare Tagesauswertungen ableiten.

> Das Repository befindet sich am Anfang der Entwicklung. Die README beschreibt die fachliche Zielsetzung und die vereinbarten Leitplanken; konkrete Entitäten, Grenzwerte und technische Implementierungsdetails werden im Verlauf der Entwicklung präzisiert.

## Zielsetzung

Das System soll insbesondere:

- Arbeitstage automatisiert erkennen und dokumentieren.
- zwischen Büro-/Präsenztagen, Homeoffice-Tagen und Nicht-Arbeitstagen unterscheiden.
- eine konfigurierbare Mindestarbeitszeit berücksichtigen, bevor ein Tag als Arbeitstag zählt.
- vorhandene Home-Assistant-Daten und -Entitäten nutzen, statt unnötig parallele Datenquellen aufzubauen.
- Tagesentscheidungen nachvollziehbar machen und Korrekturen bzw. Sonderfälle ermöglichen.
- Auswertungen bereitstellen, die bei der persönlichen Dokumentation und als Grundlage für die jährliche steuerliche Aufstellung helfen können.

Die Erfassung ist eine technische Dokumentationshilfe und ersetzt keine Prüfung der steuerlichen Anforderungen oder der tatsächlichen Arbeitszeitaufzeichnungen.

## Fachliches Konzept

### Erkennung eines Arbeitstages

Ein Kalendertag soll nicht allein deshalb als Arbeitstag zählen, weil kurzzeitig ein Gerät oder ein Ping-Sensor aktiv ist. Es soll eine **konfigurierbare Mindestarbeitszeit** geben.

Die Mindestarbeitszeit ist als veränderbarer Parameter bzw. Home-Assistant-Helfer vorzusehen. Die konkrete Auswertung soll anhand der verfügbaren Signale entscheiden, ob die Schwelle erreicht wurde. Der Grenzwert darf nicht fest im Automationscode verborgen sein.

### Erkennung von Homeoffice und Büro

Die Erkennung soll vorhandene Signale kombinieren, insbesondere:

- Anwesenheit bzw. Standort innerhalb der relevanten Home-Assistant-Zonen.
- Erreichbarkeit der bekannten Geräte/Hosts über Ping bzw. entsprechende Binary-Sensoren.
- Arbeitsort-Zone (insbesondere die Büro-/Arbeitszone).
- erkannte Arbeitsdauer und zeitlicher Verlauf der Signale.

Bekannte Beispiele aus der bestehenden Umgebung sind:

- `binary_sensor.heimsteuerung_sina_marcel_ping`
- `person.marcel`
- `zone.ble_bonn`

Diese Entity-IDs sind Startpunkte aus der bestehenden Installation, keine unveränderlichen Anforderungen. Vor einer Implementierung muss geprüft werden, welche Entitäten tatsächlich existieren und welche Semantik/Zuverlässigkeit sie haben.

### Tagesentscheidung und Nachvollziehbarkeit

Die Tagesklassifikation soll möglichst deterministisch und erklärbar sein. Für jeden ausgewerteten Tag sollte später erkennbar sein:

- welches Datum bewertet wurde,
- ob ein Arbeitstag erkannt wurde,
- ob der Tag als Homeoffice oder Büro/Präsenz klassifiziert wurde,
- welche Arbeitsdauer zugrunde lag,
- ob die Mindestarbeitszeit erreicht wurde,
- welche Daten/Signale zur Entscheidung geführt haben,
- ob die Klassifikation automatisch oder manuell korrigiert wurde.

Fehlende oder widersprüchliche Sensorwerte dürfen nicht stillschweigend zu einer scheinbar sicheren Klassifikation führen. Unklare Fälle sollen als unbekannt bzw. prüfbedürftig behandelt werden.

## Leitplanken für die Implementierung

1. **Konfigurierbarkeit:** Fachliche Grenzwerte wie die Mindestarbeitszeit müssen zentral und einfach änderbar sein.
2. **Robustheit:** Kurzzeitige Netzwerkunterbrechungen, Neustarts von Home Assistant und verspätete Sensorupdates dürfen keine doppelten oder falschen Tagesbuchungen erzeugen.
3. **Idempotenz:** Wiederholte Ausführung derselben Auswertung darf das Tagesergebnis nicht duplizieren oder ungewollt verändern.
4. **Transparenz:** Entscheidungen sollen über Status-, Diagnose- oder Protokollinformationen nachvollziehbar sein.
5. **Wartbarkeit:** Logik, Konfiguration und Darstellung sollen sauber getrennt werden. Keine unnötig komplexen Einzel-Automationen.
6. **Datensparsamkeit:** Es sollen nur die für die Tagesauswertung notwendigen Daten gespeichert werden.
7. **Sichere Änderungen:** Neue Logik wird zuerst im Beta-Kanal erprobt und erst nach Prüfung in Stable übernommen.

## Release-Kanäle

Das Projekt verwendet zwei getrennte Kanäle. **Stable** ist die empfohlene Version für den regulären Betrieb. **Beta** dient der Erprobung neuer Funktionen und Änderungen.

| | Stable | Beta |
|---|---|---|
| Zweck | Verlässlicher Regelbetrieb | Früher Zugriff auf neue Entwicklungen |
| Inhalt | Geprüfte und freigegebene Funktionen | Neue Funktionen, Änderungen und Experimente |
| Risiko | Möglichst gering | Höheres Änderungs- und Fehlerrisiko |
| Änderungen | Nur nach erfolgreicher Prüfung aus Beta übernehmen | Darf sich häufiger und auch inkompatibel ändern |
| Empfehlung | Für den produktiven Home-Assistant-Betrieb | Für Tests und kontrollierte Erprobung |

### Branch-Strategie

- `main` ist der Stable-Entwicklungs- und Veröffentlichungszweig.
- `beta` enthält die jeweils zur Erprobung vorgesehenen Änderungen.
- Neue Funktionen und Fehlerbehebungen werden zunächst in Beta entwickelt bzw. integriert.
- Nach Tests und fachlicher Freigabe werden geeignete Änderungen von `beta` nach `main` übernommen.
- Fehlerbehebungen, die Stable unmittelbar benötigt, können gezielt in `main` umgesetzt und anschließend nach `beta` zurückgeführt werden, damit die Zweige nicht auseinanderlaufen.

### Versionierung und Kennzeichnung

Es wird semantische Versionierung angestrebt:

- Stable: `vMAJOR.MINOR.PATCH`, beispielsweise `v1.2.0`.
- Beta: Vorabversionen mit Suffix, beispielsweise `v1.3.0-beta.1`.

Stable-Releases werden als GitHub-Releases bzw. Tags veröffentlicht. Beta-Stände werden klar als Vorabversion gekennzeichnet. Ein Beta-Stand ist nicht automatisch für den produktiven Betrieb freigegeben.

## Geplanter Funktionsumfang

Die Umsetzung erfolgt schrittweise. Die folgende Reihenfolge ist eine Orientierung und keine Behauptung, dass die Funktionen bereits vorhanden sind.

1. **Grundlage und Konfiguration**
   - zentrale Konfiguration der Mindestarbeitszeit
   - Definition der relevanten Zonen und Anwesenheitssignale
   - klare Definition der Tagesgrenzen und Zeitzone

2. **Erkennung**
   - Ermittlung der täglichen Arbeitsdauer
   - Erkennung von Homeoffice und Büro/Präsenz
   - Behandlung von Unterbrechungen, Neustarts und fehlenden Sensordaten

3. **Tagesprotokoll**
   - genau ein nachvollziehbares Ergebnis pro Kalendertag
   - Speicherung der Klassifikation und der relevanten Kennzahlen
   - Möglichkeit zur manuellen Korrektur bzw. Kennzeichnung von Sonderfällen

4. **Auswertung**
   - Monats- und Jahresübersichten
   - Summen für Homeoffice und Büro/Präsenz
   - Export bzw. geeignete Zusammenfassung für die persönliche Dokumentation

## Entwicklungsgrundsätze

- Änderungen möglichst klein und überprüfbar halten.
- Vor Änderungen bestehende Automationen, Helfer und Entity-IDs prüfen.
- Keine realen Entity-IDs oder Konfigurationswerte erfinden.
- Bei jeder fachlichen Änderung festhalten, welche Fälle sie abdeckt und welche Randfälle offenbleiben.
- Tests für Tagesgrenzen, Zeitzonen, Sommer-/Winterzeit, Neustarts und Sensor-Ausfälle berücksichtigen.
- Stable erst aktualisieren, wenn die Änderung im Beta-Kanal ausreichend geprüft wurde.

## Projektstatus

**Frühe Planungs- und Entwicklungsphase.** Die fachliche Richtung und die Release-Kanäle sind definiert. Implementierte Funktionen und unterstützte Home-Assistant-Versionen werden ergänzt, sobald sie tatsächlich vorhanden und getestet sind.

## Mitwirkung und Änderungen

Vor größeren Änderungen an Datenmodell, Tagesklassifikation oder Release-Struktur sollte die fachliche Auswirkung dokumentiert werden. Fehlerberichte sollten nach Möglichkeit Datum, betroffene Sensoren/Entitäten, erwartetes Ergebnis und tatsächlich beobachtetes Ergebnis enthalten. Persönliche Standort- oder Anwesenheitsdaten bitte vor dem Teilen von Logs und Screenshots entfernen.
