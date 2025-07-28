# Lernassistent für Physikaufgaben

Ein interaktives Kommandozeilen-Tool zum systematischen Lernen und Wiederholen von Physikaufgaben mit integriertem Timer und Fortschrittsverfolgung.

## 📋 Überblick

Dieses Projekt ist ein Lernassistent, der dabei hilft, Physikaufgaben strukturiert zu bearbeiten und den Lernfortschritt zu verfolgen. Das System verwendet eine Round-basierte Logik, bei der Aufgaben mit der geringsten Anzahl an Wiederholungen priorisiert werden.

## ✨ Features

- **📊 Multi-Exam Support**: Verwaltung mehrerer Prüfungen/Examina
- **🎯 Intelligente Aufgabenauswahl**: Round-basierte Logik für optimale Wiederholung
- **⏱️ Integrierter Timer**: Zeitmessung für jede Aufgabe mit Auto-Save
- **📈 Fortschrittsverfolgung**: Detaillierte Statistiken und Lernfortschritt
- **🔄 Session Recovery**: Wiederherstellung unterbrochener Lernsessions
- **📝 Punktebereich-Filter**: Auswahl von Aufgaben nach Schwierigkeitsgrad
- **💾 SQLite Datenbank**: Persistente Speicherung aller Daten

## 🚀 Installation & Setup

### Voraussetzungen
- Python 3.7+
- pandas (für CSV-Import)

### Installation
```bash
# Repository klonen
git clone https://github.com/Louber1/learn.git
cd learn

# Virtuelles Environment erstellen
python -m venv .venv

# Virtuelles Environment aktivieren
# Für Windows:
.venv\Scripts\activate
# Für macOS/Linux:
source .venv/bin/activate

# Abhängigkeiten installieren
pip install pandas

# Daten importieren (alle CSV-Dateien aus ./exams)
python import_data.py

# Hauptprogramm starten
python main.py
```

## 📁 Projektstruktur

```
learn/
├── main.py                    # Hauptprogramm
├── exam_manager.py           # Prüfungsverwaltung
├── import_data.py            # CSV-Datenimport
├── view_solution_attempts.py # Lösungsversuche anzeigen
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
1. **Aufgabe lösen**: Wähle Punktebereich und löse eine zufällige Aufgabe
2. **Zeitstatistiken anzeigen**: Zeige Lernfortschritt und Zeitstatistiken
3. **Switch exam**: Wechsle zwischen verschiedenen Prüfungen
4. **Beenden**: Programm beenden

### Prüfungen verwalten
```bash
# Prüfungen auflisten und löschen
python exam_manager.py
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
        ├── subtasks          # Teilaufgaben (z.B. "1.1a", "2b3")
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

Dieses Projekt steht unter der MIT-Lizenz. Siehe `LICENSE` Datei für Details.

## 🐛 Bekannte Probleme & Lösungen

### Import-Probleme
- **CSV nicht gefunden**: Prüfe Dateipfad und Dateiformat
- **Encoding-Fehler**: CSV sollte UTF-8 kodiert sein
- **Spalten fehlen**: Alle erforderlichen Spalten müssen vorhanden sein

### Timer-Probleme
- **Timer stoppt**: Prüfe Tastatureingaben (SPACE/ESC)
- **Session Recovery**: Nutze die Recovery-Option beim Programmstart

## 📞 Support

Bei Problemen oder Fragen:
1. Prüfe die bekannten Probleme oben
2. Erstelle ein Issue auf GitHub
3. Beschreibe das Problem mit Fehlermeldung und Schritten zur Reproduktion

---

**Viel Erfolg beim Lernen! 🎓**
