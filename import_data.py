import pandas as pd
import re
import sys
from pathlib import Path
from typing import Optional
from database.models import DatabaseManager
from exam_manager import ExamManager

def extract_main_task(task_str):
    """
    Extrahiert Hauptaufgabe aus Teilaufgabe
    Beispiele:
    '1.1a' -> '1.1'
    '1.1b' -> '1.1' 
    '2a1' -> '2'
    '2a6' -> '2'
    '3.2c4' -> '3.2'
    """
    task_str = str(task_str).strip()
    
    # Entferne alles ab dem ersten Buchstaben (und was danach kommt)
    # Das funktioniert für: 1.1a, 1.1b, 2a1, 2a6, 3.2c4, etc.
    match = re.match(r'^(\d+(?:\.\d+)*)', task_str)
    
    if match:
        return match.group(1)
    else:
        # Fallback: falls kein Pattern erkannt wird, gib original zurück
        print(f"⚠️  Unbekanntes Aufgabenformat: {task_str}")
        return task_str


def test_extract_function():
    """Testet die extract_main_task Funktion"""
    test_cases = [
        "1.1a", "1.1b", "1.2", "1.3",
        "2a1", "2a2", "2a3", "2a4", "2a5", "2a6",
        "3.2c4", "4b", "5.1.2a", "6"
    ]
    
    print("🧪 Teste extract_main_task Funktion:")
    for test in test_cases:
        result = extract_main_task(test)
        print(f"   '{test}' -> '{result}'")

def import_csv_to_db(csv_path: str, db_manager: DatabaseManager, clear_existing_exam: bool = False):
    """Importiert CSV-Daten in die Datenbank - streamlined version"""
    
    # CSV einlesen
    print(f"📖 Reading CSV file: {csv_path}")
    try:
        df = pd.read_csv(csv_path, sep=';')
        print(f"   Found: {len(df)} rows")
    except Exception as e:
        print(f"❌ Failed to read CSV file: {e}")
        raise
    
    # Auto-extract exam name from CSV
    if 'Prüfung' not in df.columns:
        print("❌ CSV must contain 'Prüfung' column")
        raise ValueError("Missing 'Prüfung' column in CSV")
    
    exam_names = df['Prüfung'].unique()
    if len(exam_names) > 1:
        print(f"⚠️  Multiple exam names found in CSV: {exam_names}")
        print("   Using the first one...")
    
    exam_name = exam_names[0]
    print(f"📋 Auto-detected exam name: {exam_name}")
    
    # Show some examples of task extraction
    print("\n🔍 Task extraction examples:")
    sample_tasks = df['Aufgabe'].unique()[:10]  # First 10 unique tasks
    for task in sample_tasks:
        main_task = extract_main_task(task)
        print(f"   '{task}' -> '{main_task}'")
    
    # Use ExamManager to handle exam creation/lookup
    exam_manager = ExamManager(db_manager)
    
    # Check if exam exists, create if not
    exam = exam_manager.get_exam_by_name(exam_name)
    if not exam:
        print(f"📋 Creating new exam: {exam_name}")
        exam_id = exam_manager.create_exam(exam_name, f"Imported from {csv_path}")
    else:
        exam_id = exam['id']
        print(f"📋 Using existing exam: {exam_name} (ID: {exam_id})")
    
    if clear_existing_exam:
        print("🗑️  Clearing existing data for this exam...")
        _clear_exam_data(db_manager, exam_id)
    
    try:
        # Import CSV data
        _import_csv_data(csv_path, db_manager, exam_id)
        
    except Exception as e:
        print(f"❌ Import failed: {e}")
        raise

def _clear_exam_data(db_manager: DatabaseManager, exam_id: int):
    """Clears all data for a specific exam (but keeps the exam record)"""
    conn = db_manager.get_connection()
    cursor = conn.cursor()
    
    try:
        # Delete in correct order
        cursor.execute('''
            DELETE FROM solution_attempts 
            WHERE task_id IN (
                SELECT t.id FROM tasks t
                JOIN worksheets w ON t.worksheet_id = w.id
                WHERE w.exam_id = ?
            )
        ''', (exam_id,))
        
        
        cursor.execute('''
            DELETE FROM tasks 
            WHERE worksheet_id IN (
                SELECT id FROM worksheets WHERE exam_id = ?
            )
        ''', (exam_id,))
        
        cursor.execute('DELETE FROM worksheets WHERE exam_id = ?', (exam_id,))
        
        conn.commit()
        print("✅ Existing exam data cleared")
        
    except Exception as e:
        conn.rollback()
        print(f"❌ Failed to clear exam data: {e}")
        raise
    finally:
        conn.close()

def _import_csv_data(csv_path: str, db_manager: DatabaseManager, exam_id: int):
    """Imports CSV data for a specific exam"""
    print(f"📖 Reading CSV file: {csv_path}")
    
    try:
        df = pd.read_csv(csv_path, sep=';')
        print(f"   Found: {len(df)} rows")
    except Exception as e:
        print(f"❌ Failed to read CSV: {e}")
        raise
    
    conn = db_manager.get_connection()
    cursor = conn.cursor()
    
    try:
        # Import worksheets
        print("\n📋 Importing worksheets...")
        worksheets = df[['Semester', 'Blatt']].drop_duplicates()
        
        for _, row in worksheets.iterrows():
            try:
                cursor.execute('''
                    INSERT OR IGNORE INTO worksheets (semester, sheet_number, exam_id)
                    VALUES (?, ?, ?)
                ''', (int(row['Semester']), int(row['Blatt']), exam_id))
                print(f"   ✅ Semester {row['Semester']}, Blatt {row['Blatt']}")
            except Exception as e:
                print(f"   ⚠️  Error with worksheet: Semester {row['Semester']}, Blatt {row['Blatt']} - {e}")
        
        conn.commit()
        
        # Group by main task and sum points
        print("\n📝 Processing tasks...")
        
        # Create a dictionary to accumulate points for each main task
        task_points = {}
        
        for index, row in df.iterrows():
            try:
                main_task = extract_main_task(row['Aufgabe'])
                # Explicitly convert to scalar values
                semester = int(pd.to_numeric(row['Semester']))
                blatt = int(pd.to_numeric(row['Blatt']))
                points = int(pd.to_numeric(row['Punkte']))
                
                # Create unique key for task
                task_key = (semester, blatt, main_task)
                
                if task_key not in task_points:
                    task_points[task_key] = 0
                
                task_points[task_key] += points
                
                # Convert index to int for arithmetic operations
                row_num = int(index) if isinstance(index, (int, float)) else 0
                if row_num % 20 == 0:
                    print(f"   📄 Processed: {row_num + 1}/{len(df)} rows")
            
            except Exception as e:
                row_num = int(index) if isinstance(index, (int, float)) else 0
                print(f"❌ Error at row {row_num + 1}: {e}")
                continue
        
        # Insert tasks with calculated total points
        print(f"\n📝 Inserting {len(task_points)} unique tasks...")
        
        for (semester, blatt, main_task), total_points in task_points.items():
            try:
                # Get worksheet ID
                cursor.execute('''
                    SELECT id FROM worksheets 
                    WHERE semester = ? AND sheet_number = ? AND exam_id = ?
                ''', (semester, blatt, exam_id))
                
                worksheet_result = cursor.fetchone()
                if worksheet_result is None:
                    print(f"❌ Worksheet not found: Semester {semester}, Blatt {blatt}")
                    continue
                
                worksheet_id = worksheet_result[0]
                
                # Insert task with total points
                cursor.execute('''
                    INSERT OR REPLACE INTO tasks (worksheet_id, task_number, total_points)
                    VALUES (?, ?, ?)
                ''', (worksheet_id, main_task, total_points))
                
            except Exception as e:
                print(f"❌ Error inserting task {main_task}: {e}")
                continue
        
        conn.commit()
        
        # Show statistics
        cursor.execute('''
            SELECT COUNT(*) FROM worksheets WHERE exam_id = ?
        ''', (exam_id,))
        worksheet_count = cursor.fetchone()[0]
        
        cursor.execute('''
            SELECT COUNT(*) FROM tasks 
            WHERE worksheet_id IN (SELECT id FROM worksheets WHERE exam_id = ?)
        ''', (exam_id,))
        task_count = cursor.fetchone()[0]
        
        print(f"\n✅ Import successful!")
        print(f"   📋 {worksheet_count} worksheets")
        print(f"   📝 {task_count} tasks")
        
    except Exception as e:
        print(f"❌ Import failed: {e}")
        conn.rollback()
        raise
    finally:
        conn.close()

def show_database_content(db_manager: DatabaseManager, limit: int = 20):
    """Zeigt den Inhalt der Datenbank"""
    conn = db_manager.get_connection()
    
    query = '''
        SELECT 
            w.semester,
            w.sheet_number,
            t.task_number,
            t.total_points,
            t.times_done
        FROM worksheets w
        JOIN tasks t ON w.id = t.worksheet_id
        ORDER BY w.semester, w.sheet_number, t.task_number
        LIMIT ?
    '''
    
    try:
        df = pd.read_sql_query(query, conn, params=[limit])
        print(f"\n📊 Datenbank-Inhalt (erste {limit} Aufgaben):")
        print(df.to_string(index=False))
        
        # Zeige auch Statistik nach Punkten
        stats_query = '''
            SELECT 
                t.total_points,
                COUNT(*) as count
            FROM tasks t
            GROUP BY t.total_points
            ORDER BY t.total_points
        '''
        stats_df = pd.read_sql_query(stats_query, conn)
        print(f"\n📈 Aufgaben nach Punkten:")
        print(stats_df.to_string(index=False))
        
    except Exception as e:
        print(f"❌ Fehler beim Anzeigen der Datenbank: {e}")
    finally:
        conn.close()

def show_progress_overview(db_manager: DatabaseManager):
    """Zeigt Übersicht über den Lernfortschritt"""
    conn = db_manager.get_connection()
    
    query = '''
        SELECT 
            t.total_points,
            COUNT(*) as total_tasks,
            SUM(CASE WHEN t.times_done = 0 THEN 1 ELSE 0 END) as new_tasks,
            SUM(CASE WHEN t.times_done > 0 THEN 1 ELSE 0 END) as done_tasks,
            ROUND(AVG(CAST(t.times_done AS FLOAT)), 2) as avg_repetitions
        FROM tasks t
        GROUP BY t.total_points
        ORDER BY t.total_points
    '''
    
    try:
        df = pd.read_sql_query(query, conn)
        print(f"\n📊 Lernfortschritt nach Punkten:")
        print(f"{'Punkte':<8} {'Gesamt':<8} {'Offen':<8} {'Fertig':<8} {'⌀ Wiederh.':<12}")
        print("-" * 50)
        
        for _, row in df.iterrows():
            print(f"{row['total_points']:<8} {row['total_tasks']:<8} {row['new_tasks']:<8} {row['done_tasks']:<8} {row['avg_repetitions']:<12}")
        
    except Exception as e:
        print(f"❌ Fehler beim Anzeigen des Fortschritts: {e}")
    finally:
        conn.close()

def import_all_exams_from_directory(exams_dir: str, db_manager: DatabaseManager, clear_existing_exams: bool = False):
    """Imports all CSV files from the exams directory"""
    exams_path = Path(exams_dir)
    
    if not exams_path.exists():
        print(f"❌ Exams directory not found: {exams_dir}")
        return
    
    # Find all CSV files in the directory
    csv_files = list(exams_path.glob("*.csv"))
    
    if not csv_files:
        print(f"❌ No CSV files found in directory: {exams_dir}")
        return
    
    print(f"📁 Found {len(csv_files)} CSV files in {exams_dir}:")
    for csv_file in csv_files:
        print(f"   📄 {csv_file.name}")
    
    print("\n" + "="*60)
    print("📥 IMPORTING ALL EXAMS FROM DIRECTORY")
    print("="*60)
    
    successful_imports = 0
    failed_imports = 0
    
    for csv_file in csv_files:
        print(f"\n{'='*40}")
        print(f"📥 Processing: {csv_file.name}")
        print(f"{'='*40}")
        
        try:
            import_csv_to_db(str(csv_file), db_manager, clear_existing_exams)
            successful_imports += 1
            print(f"✅ Successfully imported: {csv_file.name}")
            
        except Exception as e:
            failed_imports += 1
            print(f"❌ Failed to import {csv_file.name}: {e}")
            continue
    
    print("\n" + "="*60)
    print("📊 IMPORT SUMMARY")
    print("="*60)
    print(f"✅ Successful imports: {successful_imports}")
    print(f"❌ Failed imports: {failed_imports}")
    print(f"📄 Total files processed: {len(csv_files)}")
    
    if successful_imports > 0:
        print("\n📊 Overall database overview:")
        show_database_content(db_manager, limit=15)

def main():
    """Import CSV data - supports single files or all files from exams directory"""
    
    # Initialize database
    print("🔧 Initializing database...")
    db_manager = DatabaseManager()
    db_manager.init_database()
    
    # Check if we should import all exams from directory (default behavior)
    if len(sys.argv) == 1:
        # No arguments - import all from ./exams directory
        print("📁 No specific file provided - importing all exams from ./exams directory")
        import_all_exams_from_directory("./exams", db_manager, clear_existing_exams=False)
        return
    
    # Check for --all flag
    if "--all" in sys.argv:
        clear_existing_exams = "--clear-exams" in sys.argv
        print("📁 Importing all exams from ./exams directory")
        if clear_existing_exams:
            print("⚠️  Will clear existing exam data before import")
        import_all_exams_from_directory("./exams", db_manager, clear_existing_exams)
        return
    
    # Single file import (legacy behavior)
    if len(sys.argv) < 2:
        print("❌ Usage:")
        print("   python import_data.py                    # Import all CSV files from ./exams")
        print("   python import_data.py --all              # Import all CSV files from ./exams")
        print("   python import_data.py --all --clear-exams # Import all, clearing existing data")
        print("   python import_data.py <csv_file>         # Import specific CSV file")
        print("   python import_data.py <csv_file> --clear-exam # Import specific file, clear existing")
        sys.exit(1)
    
    csv_file = sys.argv[1]
    clear_existing_exam = "--clear-exam" in sys.argv
    
    # Check if CSV file exists
    if not Path(csv_file).exists():
        print(f"❌ CSV file not found: {csv_file}")
        sys.exit(1)
    
    print("=" * 60)
    print("📥 SINGLE FILE CSV IMPORT")
    print("=" * 60)
    
    # Import single CSV
    try:
        print(f"\n📥 Starting import from: {csv_file}")
        if clear_existing_exam:
            print("⚠️  Will clear existing exam data before import")
        
        import_csv_to_db(csv_file, db_manager, clear_existing_exam)
        
        print("\n" + "="*60)
        print("✅ IMPORT SUCCESSFUL!")
        print("="*60)
        
        # Show brief overview
        print("\n📊 Quick overview:")
        show_database_content(db_manager, limit=10)
        
    except Exception as e:
        print(f"\n❌ Import failed: {e}")
        sys.exit(1)

if __name__ == "__main__":
    main()
