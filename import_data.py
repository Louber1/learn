import sqlite3
import pandas as pd
import re
from pathlib import Path

def init_database(db_path="physics_tasks.db"):
    """Initialisiert die Datenbank mit den Tabellen"""
    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()
    
    # Tabellen erstellen
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS worksheets (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            semester INTEGER NOT NULL,
            sheet_number INTEGER NOT NULL,
            UNIQUE(semester, sheet_number)
        )
    ''')
    
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS tasks (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            worksheet_id INTEGER NOT NULL,
            task_number TEXT NOT NULL,
            total_points INTEGER DEFAULT 0,
            times_done INTEGER DEFAULT 0,
            FOREIGN KEY (worksheet_id) REFERENCES worksheets(id),
            UNIQUE(worksheet_id, task_number)
        )
    ''')
    
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS subtasks (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            task_id INTEGER NOT NULL,
            subtask_name TEXT NOT NULL,
            points INTEGER NOT NULL,
            FOREIGN KEY (task_id) REFERENCES tasks(id),
            UNIQUE(task_id, subtask_name)
        )
    ''')
    
    conn.commit()
    conn.close()

def extract_main_task(task_str):
    """Extrahiert Hauptaufgabe aus Teilaufgabe (z.B. '1.1a' -> '1.1')"""
    return re.sub(r'[a-zA-Z]+$', '', str(task_str))

def clear_database(db_path="physics_tasks.db"):
    """Löscht alle Daten aus der Datenbank"""
    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()
    
    cursor.execute('DELETE FROM subtasks')
    cursor.execute('DELETE FROM tasks')
    cursor.execute('DELETE FROM worksheets')
    
    conn.commit()
    conn.close()

def import_csv_to_db(csv_path, db_path="physics_tasks.db"):
    """Importiert CSV-Daten in die Datenbank"""
    
    # CSV einlesen
    print(f"📖 Lese CSV-Datei: {csv_path}")
    df = pd.read_csv(csv_path, sep=';')
    print(f"   Gefunden: {len(df)} Zeilen")
    
    # Datenbank leeren für sauberen Import
    clear_database(db_path)
    
    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()
    
    try:
        # Worksheets einfügen
        print("📋 Importiere Arbeitsblätter...")
        worksheets = df[['Semester', 'Blatt']].drop_duplicates()
        
        for _, row in worksheets.iterrows():
            try:
                cursor.execute('''
                    INSERT INTO worksheets (semester, sheet_number)
                    VALUES (?, ?)
                ''', (int(row['Semester']), int(row['Blatt'])))
                print(f"   ✅ Semester {row['Semester']}, Blatt {row['Blatt']}")
            except sqlite3.IntegrityError:
                print(f"   ⚠️  Worksheet bereits vorhanden: Semester {row['Semester']}, Blatt {row['Blatt']}")
        
        conn.commit()
        
        # Tasks und Subtasks verarbeiten
        print("📝 Verarbeite Aufgaben...")
        
        for index, row in df.iterrows():
            try:
                main_task = extract_main_task(row['Aufgabe'])
                
                # Worksheet ID holen
                cursor.execute('''
                    SELECT id FROM worksheets 
                    WHERE semester = ? AND sheet_number = ?
                ''', (int(row['Semester']), int(row['Blatt'])))
                
                worksheet_result = cursor.fetchone()
                if worksheet_result is None:
                    print(f"❌ Worksheet nicht gefunden: Semester {row['Semester']}, Blatt {row['Blatt']}")
                    continue
                
                worksheet_id = worksheet_result[0]
                
                # Task einfügen (falls nicht vorhanden)
                cursor.execute('''
                    INSERT OR IGNORE INTO tasks (worksheet_id, task_number, total_points)
                    VALUES (?, ?, 0)
                ''', (worksheet_id, main_task))
                
                # Task ID holen
                cursor.execute('''
                    SELECT id FROM tasks 
                    WHERE worksheet_id = ? AND task_number = ?
                ''', (worksheet_id, main_task))
                
                task_result = cursor.fetchone()
                if task_result is None:
                    print(f"❌ Task nicht gefunden: {main_task}")
                    continue
                
                task_id = task_result[0]
                
                # Subtask einfügen
                cursor.execute('''
                    INSERT OR IGNORE INTO subtasks (task_id, subtask_name, points)
                    VALUES (?, ?, ?)
                ''', (task_id, row['Aufgabe'], int(row['Punkte'])))
                
                if index % 10 == 0:  # Fortschritt anzeigen
                    print(f"   📄 Verarbeitet: {index + 1}/{len(df)} Zeilen")
                
            except Exception as e:
                print(f"❌ Fehler bei Zeile {index + 1}: {e}")
                print(f"   Daten: {row.to_dict()}")
                continue
        
        conn.commit()
        
        # Total Points für Tasks berechnen
        print("🔢 Berechne Gesamtpunkte...")
        cursor.execute('''
            UPDATE tasks 
            SET total_points = (
                SELECT SUM(points) 
                FROM subtasks 
                WHERE subtasks.task_id = tasks.id
            )
        ''')
        
        conn.commit()
        
        # Statistik ausgeben
        cursor.execute('SELECT COUNT(*) FROM worksheets')
        worksheet_count = cursor.fetchone()[0]
        
        cursor.execute('SELECT COUNT(*) FROM tasks')
        task_count = cursor.fetchone()[0]
        
        cursor.execute('SELECT COUNT(*) FROM subtasks')
        subtask_count = cursor.fetchone()[0]
        
        print(f"\n✅ Import erfolgreich!")
        print(f"   📋 {worksheet_count} Arbeitsblätter")
        print(f"   📝 {task_count} Hauptaufgaben")
        print(f"   📄 {subtask_count} Teilaufgaben")
        
    except Exception as e:
        print(f"❌ Fehler beim Import: {e}")
        conn.rollback()
    finally:
        conn.close()

def show_database_content(db_path="physics_tasks.db"):
    """Zeigt den Inhalt der Datenbank"""
    conn = sqlite3.connect(db_path)
    
    query = '''
        SELECT 
            w.semester,
            w.sheet_number,
            t.task_number,
            t.total_points,
            t.times_done,
            GROUP_CONCAT(s.subtask_name || ' (' || s.points || 'P)', ', ') as subtasks
        FROM worksheets w
        JOIN tasks t ON w.id = t.worksheet_id
        JOIN subtasks s ON t.id = s.task_id
        GROUP BY w.semester, w.sheet_number, t.task_number
        ORDER BY w.semester, w.sheet_number, t.task_number
    '''
    
    try:
        df = pd.read_sql_query(query, conn)
        print("\n📊 Datenbank-Inhalt:")
        print(df.to_string(index=False))
    except Exception as e:
        print(f"❌ Fehler beim Anzeigen der Datenbank: {e}")
    finally:
        conn.close()

def debug_csv(csv_path):
    """Debug-Funktion um CSV-Struktur zu prüfen"""
    print(f"🔍 Debug CSV: {csv_path}")
    df = pd.read_csv(csv_path, sep=';')
    print(f"Spalten: {df.columns.tolist()}")
    print(f"Erste 3 Zeilen:")
    print(df.head(3))
    print(f"Datentypen:")
    print(df.dtypes)
    print(f"Unique Semester: {df['Semester'].unique()}")
    print(f"Unique Blatt: {df['Blatt'].unique()}")

if __name__ == "__main__":
    # Datenbank initialisieren
    init_database()
    
    # CSV importieren
    csv_file = "ExPhs1&2-Aufgaben-Punkte.csv"
    if Path(csv_file).exists():
        # Debug CSV erst anzeigen
        debug_csv(csv_file)
        
        print("\n" + "="*50)
        import_csv_to_db(csv_file)
        show_database_content()
    else:
        print(f"❌ CSV-Datei '{csv_file}' nicht gefunden!")