# Lernassistent für Physikaufgaben

Ein interaktives Kommandozeilen-Tool zum systematischen Lernen und Wiederholen von Physikaufgaben mit integriertem Timer und Fortschrittsverfolgung.

## 📋 Überblick

Dieses Projekt ist ein Lernassistent, der dabei hilft, Physikaufgaben strukturiert zu bearbeiten und den Lernfortschritt zu verfolgen. Das System verwendet eine Round-basierte Logik, bei der Aufgaben mit der geringsten Anzahl an Wiederholungen priorisiert werden.

## ✨ Features

- **📊 Multi-Exam Support**: Verwaltung mehrerer Prüfungen/Examina
- **🎯 Intelligente Aufgabenauswahl**: Round-basierte Logik für optimale Wiederholung
- **⏱️ Zeit/Punkt-basierte Auswahl**: Gezielte Auswahl von Aufgaben mit längster Bearbeitungszeit pro Punkt
- **⏱️ Integrierter Timer**: Zeitmessung für jede Aufgabe mit Auto-Save
- **📈 Fortschrittsverfolgung**: Detaillierte Statistiken und Lernfortschritt
- **🔄 Session Recovery**: Wiederherstellung unterbrochener Lernsessions
- **📝 Punktebereich-Filter**: Auswahl von Aufgaben nach Schwierigkeitsgrad
- **💾 SQLite Datenbank**: Persistente Speicherung aller Daten

## 🚀 Installation & Setup

### Voraussetzungen

- **uv** – Ein extrem schneller Python-Paket- und Projektmanager, geschrieben in Rust.  
  Installationsanleitung: [uv Installation](https://docs.astral.sh/uv/getting-started/installation/)
- **Python** – Version 3.7 oder höher.

### Installation
```bash
# Repository klonen
gh repo clone Louber1/learn
cd learn

# Virtuelles Environment erstellen
uv venv

# Virtuelles Environment aktivieren
# Für Windows:
.venv\Scripts\activate
# Für macOS/Linux:
source .venv/bin/activate

# Abhängigkeiten installieren
uv pip install -r requirements.txt

# Daten importieren (alle CSV-Dateien aus ./exams)
python import_data.py

# Hauptprogramm starten
python main.py
```

## 📁 Projektstruktur

```
learn/
├── main.py                    # Hauptprogramm
├── import_data.py            # CSV-Datenimport
├── view_solution_attempts.py # Lösungsversuche anzeigen
├── analytics.ipynb           # Statistiken
├── database/
│   └── models.py            # Datenbankmodelle und Repository-Klassen
├── services/
│   └── task_service.py      # Aufgaben-Business-Logic
├── ui/
│   └── console_ui.py        # Benutzeroberfläche
├── timer/
│   └── timer.py             # Timer-Funktionalität
├── utils/
│   └── keyboard.py          # Eingabe-Utilities
└── exams/                   # CSV-Dateien mit Aufgaben
    └── ExPhs1&2-25.csv     # Beispiel-Prüfungsdaten
```

## 📥 Daten importieren

### CSV-Format
Die CSV-Dateien müssen folgende Spalten enthalten:
- `Prüfung`: Name der Prüfung
- `Semester`: Semester-Nummer
- `Blatt`: Übungsblatt-Nummer
- `Aufgabe`: Aufgaben-/Teilaufgaben-Bezeichnung (z.B. "1.1a", "2b3")
- `Punkte`: Punktzahl der (Teil-)Aufgabe

### Import-Optionen

```bash
# Alle CSV-Dateien aus ./exams importieren (Standard)
python import_data.py

# Alle CSV-Dateien importieren
python import_data.py --all

# Alle importieren und bestehende Daten löschen
python import_data.py --all --clear-exams

# Einzelne CSV-Datei importieren
python import_data.py path/to/exam.csv

# Einzelne Datei mit Löschung bestehender Daten
python import_data.py path/to/exam.csv --clear-exam
```

## 🎮 Verwendung

### Hauptprogramm starten
```bash
python main.py
```

### Menü-Optionen
1. **Aufgabe lösen (zufällig)**: Wähle Punktebereich und löse eine zufällige Aufgabe basierend auf der Round-Logik
2. **Aufgabe mit längster Zeit/Punkt lösen**: Wähle die Aufgabe aus dem Punktebereich, deren letzter Versuch die längste Zeit pro Punkt benötigt hat
3. **Switch exam**: Wechsle zwischen verschiedenen Prüfungen
4. **Beenden**: Programm beenden

### Statistiken anzeigen
```bash
# Statistiken zur Geschwindigkeit und Anzahl der gelösten Aufgaben anzeigen
analytics.ipynb
```

### Lösungsversuche anzeigen
```bash
# Alle Lösungsversuche anzeigen
python view_solution_attempts.py
```

## 🧠 Lern-Algorithmus

Das System verwendet eine **Round-basierte Logik**:

1. **Round 1**: Alle neuen Aufgaben (0x gelöst)
2. **Round 2**: Alle Aufgaben, die 1x gelöst wurden
3. **Round 3**: Alle Aufgaben, die 2x gelöst wurden
4. usw.

**Auswahllogik**:
- Finde die niedrigste Wiederholungsanzahl im gewählten Punktebereich
- Wähle zufällig eine Aufgabe aus dieser "Round"
- Erst wenn alle Aufgaben einer Round abgeschlossen sind, geht es zur nächsten

### 🎯 Zeit/Punkt-basierte Auswahl

Zusätzlich zur Round-basierten Logik bietet das System eine **Zeit/Punkt-basierte Auswahl**:

- **Zweck**: Identifiziert Aufgaben, die beim letzten Versuch überdurchschnittlich lange pro Punkt gedauert haben
- **Algorithmus**: Berechnet für jede Aufgabe die Zeit pro Punkt des letzten Versuchs und wählt die langsamste aus
- **Nutzen**: Ermöglicht gezieltes Üben von Aufgaben, die noch Schwierigkeiten bereiten
- **Anzeige**: Zeigt die letzte benötigte Zeit und Zeit pro Punkt in der Aufgabenübersicht an

## ⏱️ Timer-Features

- **Automatischer Start**: Timer startet beim Aufgabenaufruf
- **Pausieren**: `SPACE` drücken zum Pausieren/Fortsetzen
- **Auto-Save**: Fortschritt wird alle 10 Sekunden gespeichert
- **Session Recovery**: Unterbrochene Sessions können wiederhergestellt werden
- **Abbrechen**: `ESC` zum Abbrechen der aktuellen Aufgabe

## 📊 Statistiken

Das System verfolgt:
- **Gesamtzeit** pro Aufgabe
- **Anzahl der Versuche** pro Aufgabe
- **Durchschnittszeiten** nach Punktebereichen
- **Lernfortschritt** (neue vs. wiederholte Aufgaben)
- **Round-Informationen** für jeden Punktebereich

## 🗄️ Datenbankschema

```sql
exams           # Prüfungen
├── worksheets  # Übungsblätter
    ├── tasks   # Hauptaufgaben (z.B. "1.1", "2")
        └── solution_attempts # Lösungsversuche mit Zeitmessung
```

## 🔧 Konfiguration

- **Datenbank**: `physics_tasks.db` (SQLite)
- **Auto-Save Intervall**: 10 Sekunden
- **CSV-Trennzeichen**: Semikolon (`;`)

## 🤝 Beitragen

1. Fork das Repository
2. Erstelle einen Feature-Branch (`git checkout -b feature/AmazingFeature`)
3. Committe deine Änderungen (`git commit -m 'Add some AmazingFeature'`)
4. Push zum Branch (`git push origin feature/AmazingFeature`)
5. Öffne einen Pull Request

## 📝 Lizenz

Dieses Projekt steht unter der Unlicense-Lizenz. Siehe `LICENSE` Datei für Details.

---

**Viel Erfolg beim Lernen! 🎓**
