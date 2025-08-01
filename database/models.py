import sqlite3
from datetime import datetime, date
from typing import List, Dict, Optional, Tuple

class DatabaseManager:
    def __init__(self, db_path="physics_tasks.db"):
        self.db_path = db_path
    
    def get_connection(self):
        return sqlite3.connect(self.db_path)
    
    def init_database(self):
        """Initialisiert die Datenbank mit allen Tabellen"""
        conn = self.get_connection()
        cursor = conn.cursor()
        
        # Exams (new top-level table)
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS exams (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                name TEXT NOT NULL UNIQUE,
                description TEXT,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        ''')
        
        # Worksheets (now references exams)
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS worksheets (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                semester INTEGER NOT NULL,
                sheet_number INTEGER NOT NULL,
                exam_id INTEGER,
                FOREIGN KEY (exam_id) REFERENCES exams(id),
                UNIQUE(exam_id, semester, sheet_number)
            )
        ''')
        
        # Tasks
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
        
        
        # Solution attempts
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS solution_attempts (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                task_id INTEGER NOT NULL,
                attempt_date DATE NOT NULL,
                total_time_seconds INTEGER,
                status TEXT DEFAULT 'completed',
                last_updated TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (task_id) REFERENCES tasks(id)
            )
        ''')
        
        # Migrate existing data if needed
        self._migrate_existing_data(cursor)
        
        conn.commit()
        conn.close()
    
    def _migrate_existing_data(self, cursor):
        """Migriert bestehende Daten für Rückwärtskompatibilität"""
        # Check if status column exists
        cursor.execute("PRAGMA table_info(solution_attempts)")
        columns = [column[1] for column in cursor.fetchall()]
        
        if 'status' not in columns:
            # Add status column
            cursor.execute('''
                ALTER TABLE solution_attempts 
                ADD COLUMN status TEXT DEFAULT 'completed'
            ''')
            
        if 'last_updated' not in columns:
            # Add last_updated column (SQLite doesn't support CURRENT_TIMESTAMP in ALTER TABLE)
            cursor.execute('''
                ALTER TABLE solution_attempts 
                ADD COLUMN last_updated TIMESTAMP
            ''')
        
        # Migrate existing records
        cursor.execute('''
            UPDATE solution_attempts 
            SET status = CASE 
                WHEN total_time_seconds IS NOT NULL THEN 'completed'
                ELSE 'cancelled'
            END,
            last_updated = COALESCE(created_at, CURRENT_TIMESTAMP)
            WHERE status IS NULL OR status = 'completed'
        ''')
        


class TaskRepository:
    def __init__(self, db_manager: DatabaseManager, exam_id: Optional[int] = None):
        self.db_manager = db_manager
        self.exam_id = exam_id
    
    def set_exam_id(self, exam_id: int):
        """Sets the current exam ID for filtering"""
        self.exam_id = exam_id
    
    def get_random_task(self, min_points: int, max_points: int) -> Optional[Dict]:
        """Wählt zufällige Aufgabe im Punktebereich mit Round-basierter Logik"""
        conn = self.db_manager.get_connection()
        cursor = conn.cursor()
        
        # Step 1: Find minimum completion level in the point range
        min_completion_level = self._get_min_completion_level(cursor, min_points, max_points)
        
        if min_completion_level is None:
            conn.close()
            return None
        
        # Step 2: Get all tasks at the minimum completion level
        tasks_at_min_level = self._get_tasks_at_completion_level(
            cursor, min_points, max_points, min_completion_level
        )
        
        if not tasks_at_min_level:
            conn.close()
            return None
        
        # Step 3: Randomly select from tasks at minimum completion level
        from random import choice
        task = choice(tasks_at_min_level)
        
        conn.close()
        return {
            'id': task[2],
            'semester': task[0],
            'sheet_number': task[1],
            'task_number': task[3],
            'total_points': task[4],
            'times_done': task[5],
            'is_repeat': task[5] > 0
        }
    
    def _get_min_completion_level(self, cursor, min_points: int, max_points: int) -> Optional[int]:
        """Findet das minimale times_done Level im Punktebereich"""
        query = '''
            SELECT MIN(t.times_done)
            FROM worksheets w
            JOIN tasks t ON w.id = t.worksheet_id
            WHERE t.total_points >= ? AND t.total_points <= ?
        '''
        
        params = [min_points, max_points]
        if self.exam_id:
            query += ' AND w.exam_id = ?'
            params.append(self.exam_id)
        
        cursor.execute(query, params)
        result = cursor.fetchone()
        return result[0] if result and result[0] is not None else None
    
    def _get_tasks_at_completion_level(self, cursor, min_points: int, max_points: int, completion_level: int) -> List:
        """Holt alle Aufgaben mit einem bestimmten times_done Level"""
        query = '''
            SELECT 
                w.semester,
                w.sheet_number,
                t.id,
                t.task_number,
                t.total_points,
                t.times_done
            FROM worksheets w
            JOIN tasks t ON w.id = t.worksheet_id
            WHERE t.total_points >= ? AND t.total_points <= ? AND t.times_done = ?
        '''
        
        params = [min_points, max_points, completion_level]
        if self.exam_id:
            query += ' AND w.exam_id = ?'
            params.append(self.exam_id)
        
        cursor.execute(query, params)
        return cursor.fetchall()
    
    def mark_task_done(self, task_id: int):
        """Markiert Aufgabe als erledigt"""
        conn = self.db_manager.get_connection()
        cursor = conn.cursor()
        
        cursor.execute('''
            UPDATE tasks 
            SET times_done = times_done + 1
            WHERE id = ?
        ''', (task_id,))
        
        conn.commit()
        conn.close()
    
    def get_task_counts_by_point_range(self, min_points: int, max_points: int) -> Dict[str, int]:
        """Gibt Anzahl der Aufgaben im Punktebereich zurück mit Round-Informationen"""
        conn = self.db_manager.get_connection()
        cursor = conn.cursor()
        
        # Get minimum completion level (current round)
        min_completion_level = self._get_min_completion_level(cursor, min_points, max_points)
        
        if min_completion_level is None:
            conn.close()
            return {
                'total': 0,
                'completed': 0,
                'remaining': 0,
                'current_round': 1,
                'tasks_at_current_level': 0
            }
        
        # Build queries with optional exam filtering
        total_query = '''
            SELECT COUNT(*) 
            FROM tasks t
            JOIN worksheets w ON t.worksheet_id = w.id
            WHERE t.total_points >= ? AND t.total_points <= ?
        '''
        
        completed_query = '''
            SELECT COUNT(*) 
            FROM tasks t
            JOIN worksheets w ON t.worksheet_id = w.id
            WHERE t.total_points >= ? AND t.total_points <= ? AND t.times_done > 0
        '''
        
        current_level_query = '''
            SELECT COUNT(*) 
            FROM tasks t
            JOIN worksheets w ON t.worksheet_id = w.id
            WHERE t.total_points >= ? AND t.total_points <= ? AND t.times_done = ?
        '''
        
        params = [min_points, max_points]
        if self.exam_id:
            total_query += ' AND w.exam_id = ?'
            completed_query += ' AND w.exam_id = ?'
            current_level_query += ' AND w.exam_id = ?'
            params.append(self.exam_id)
        
        # Gesamtanzahl der Aufgaben im Punktebereich
        cursor.execute(total_query, params)
        total_tasks = cursor.fetchone()[0]
        
        # Anzahl der erledigten Aufgaben (times_done > 0)
        cursor.execute(completed_query, params)
        completed_tasks = cursor.fetchone()[0]
        
        # Anzahl der Aufgaben auf dem aktuellen Level
        current_level_params = [min_points, max_points, min_completion_level]
        if self.exam_id:
            current_level_params.append(self.exam_id)
        
        cursor.execute(current_level_query, current_level_params)
        tasks_at_current_level = cursor.fetchone()[0]
        
        conn.close()
        
        return {
            'total': total_tasks,
            'completed': completed_tasks,
            'remaining': total_tasks - completed_tasks,
            'current_round': min_completion_level + 1,  # Round is 1-based (0 times done = Round 1)
            'tasks_at_current_level': tasks_at_current_level
        }


class ExamRepository:
    def __init__(self, db_manager: DatabaseManager):
        self.db_manager = db_manager
    
    def list_exams(self) -> List[Dict]:
        """Lists all available exams"""
        conn = self.db_manager.get_connection()
        cursor = conn.cursor()
        
        cursor.execute('''
            SELECT 
                e.id,
                e.name,
                e.description,
                e.created_at,
                COUNT(w.id) as worksheet_count,
                COUNT(DISTINCT t.id) as task_count
            FROM exams e
            LEFT JOIN worksheets w ON e.id = w.exam_id
            LEFT JOIN tasks t ON w.id = t.worksheet_id
            GROUP BY e.id, e.name, e.description, e.created_at
            ORDER BY e.created_at
        ''')
        
        results = cursor.fetchall()
        conn.close()
        
        exams = []
        for row in results:
            exams.append({
                'id': row[0],
                'name': row[1],
                'description': row[2],
                'created_at': row[3],
                'worksheet_count': row[4],
                'task_count': row[5]
            })
        
        return exams
    
    def get_exam_by_name(self, name: str) -> Optional[Dict]:
        """Gets exam by name"""
        conn = self.db_manager.get_connection()
        cursor = conn.cursor()
        
        cursor.execute('''
            SELECT id, name, description, created_at
            FROM exams
            WHERE name = ?
        ''', (name,))
        
        result = cursor.fetchone()
        conn.close()
        
        if result:
            return {
                'id': result[0],
                'name': result[1],
                'description': result[2],
                'created_at': result[3]
            }
        return None
    
    def create_exam(self, name: str, description: Optional[str] = None) -> int:
        """Creates a new exam (used internally by import system)"""
        conn = self.db_manager.get_connection()
        cursor = conn.cursor()
        
        try:
            cursor.execute('''
                INSERT INTO exams (name, description)
                VALUES (?, ?)
            ''', (name, description))
            
            exam_id = cursor.lastrowid
            if exam_id is None:
                raise RuntimeError("Failed to create exam - no ID returned")
            
            conn.commit()
            return exam_id
            
        except Exception as e:
            conn.rollback()
            raise
        finally:
            conn.close()


class AttemptRepository:
    def __init__(self, db_manager: DatabaseManager):
        self.db_manager = db_manager
    
    def create_attempt(self, task_id: int, status: str = 'in_progress') -> int:
        """Erstellt einen neuen Lösungsversuch"""
        conn = self.db_manager.get_connection()
        cursor = conn.cursor()
        
        cursor.execute('''
            INSERT INTO solution_attempts (task_id, attempt_date, status)
            VALUES (?, ?, ?)
        ''', (task_id, date.today(), status))
        
        attempt_id = cursor.lastrowid
        if attempt_id is None:
            conn.close()
            raise RuntimeError("Failed to create solution attempt - no ID returned")
        
        conn.commit()
        conn.close()
        
        return attempt_id
    
    def update_attempt_status(self, attempt_id: int, status: str, total_time: Optional[int] = None):
        """Aktualisiert Status und optional Zeit eines Versuchs"""
        conn = self.db_manager.get_connection()
        cursor = conn.cursor()
        
        if total_time is not None:
            cursor.execute('''
                UPDATE solution_attempts 
                SET status = ?, total_time_seconds = ?, last_updated = CURRENT_TIMESTAMP
                WHERE id = ?
            ''', (status, total_time, attempt_id))
        else:
            cursor.execute('''
                UPDATE solution_attempts 
                SET status = ?, last_updated = CURRENT_TIMESTAMP
                WHERE id = ?
            ''', (status, attempt_id))
        
        conn.commit()
        conn.close()
    
    def auto_save_progress(self, attempt_id: int, current_time: int):
        """Speichert aktuellen Fortschritt (Auto-Save)"""
        conn = self.db_manager.get_connection()
        cursor = conn.cursor()
        
        cursor.execute('''
            UPDATE solution_attempts 
            SET total_time_seconds = ?, last_updated = CURRENT_TIMESTAMP
            WHERE id = ? AND status = 'in_progress'
        ''', (current_time, attempt_id))
        
        conn.commit()
        conn.close()
    
    def get_incomplete_attempts(self) -> List[Dict]:
        """Holt unvollständige Versuche für Recovery"""
        conn = self.db_manager.get_connection()
        cursor = conn.cursor()
        
        cursor.execute('''
            SELECT 
                sa.id,
                sa.task_id,
                sa.total_time_seconds,
                sa.attempt_date,
                sa.last_updated,
                PRINTF('Sem%d Bl%d Aufg%s', w.semester, w.sheet_number, t.task_number) as task_info,
                t.total_points
            FROM solution_attempts sa
            JOIN tasks t ON sa.task_id = t.id
            JOIN worksheets w ON t.worksheet_id = w.id
            WHERE sa.status = 'in_progress'
            ORDER BY sa.last_updated DESC
        ''')
        
        results = cursor.fetchall()
        conn.close()
        
        attempts = []
        for row in results:
            attempts.append({
                'attempt_id': row[0],
                'task_id': row[1],
                'elapsed_time': row[2] or 0,
                'attempt_date': row[3],
                'last_updated': row[4],
                'task_info': row[5],
                'total_points': row[6]
            })
        
        return attempts
    
    def get_task_by_attempt(self, attempt_id: int) -> Optional[Dict]:
        """Holt Task-Informationen für einen Versuch"""
        conn = self.db_manager.get_connection()
        cursor = conn.cursor()
        
        cursor.execute('''
            SELECT 
                t.id,
                w.semester,
                w.sheet_number,
                t.task_number,
                t.total_points,
                t.times_done
            FROM solution_attempts sa
            JOIN tasks t ON sa.task_id = t.id
            JOIN worksheets w ON t.worksheet_id = w.id
            WHERE sa.id = ?
        ''', (attempt_id,))
        
        result = cursor.fetchone()
        conn.close()
        
        if not result:
            return None
        
        return {
            'id': result[0],
            'semester': result[1],
            'sheet_number': result[2],
            'task_number': result[3],
            'total_points': result[4],
            'times_done': result[5],
            'is_repeat': result[5] > 0
        }

    def get_statistics(self, task_id: Optional[int] = None) -> List[Tuple]:
        """Holt Zeitstatistiken"""
        conn = self.db_manager.get_connection()
        cursor = conn.cursor()
        
        if task_id:
            cursor.execute('''
                SELECT 
                    sa.attempt_date,
                    sa.total_time_seconds
                FROM solution_attempts sa
                WHERE sa.task_id = ?
                ORDER BY sa.attempt_date DESC
            ''', (task_id,))
        else:
            cursor.execute('''
                SELECT 
                    PRINTF('Sem%d Bl%d Aufg%s', w.semester, w.sheet_number, t.task_number) as task_info,
                    COUNT(sa.id) as attempts,
                    AVG(sa.total_time_seconds) as avg_time,
                    MIN(sa.total_time_seconds) as best_time,
                    MAX(sa.total_time_seconds) as worst_time
                FROM tasks t
                JOIN worksheets w ON t.worksheet_id = w.id
                LEFT JOIN solution_attempts sa ON t.id = sa.task_id
                WHERE sa.total_time_seconds IS NOT NULL
                GROUP BY t.id
                ORDER BY attempts DESC
                LIMIT 10
            ''')
        
        results = cursor.fetchall()
        conn.close()
        
        return results
