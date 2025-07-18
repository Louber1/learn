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
        
        # Worksheets
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS worksheets (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                semester INTEGER NOT NULL,
                sheet_number INTEGER NOT NULL,
                UNIQUE(semester, sheet_number)
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
        
        # Subtasks
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
        
        # Solution attempts
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS solution_attempts (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                task_id INTEGER NOT NULL,
                attempt_date DATE NOT NULL,
                total_time_seconds INTEGER,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (task_id) REFERENCES tasks(id)
            )
        ''')
        
        
        conn.commit()
        conn.close()


class TaskRepository:
    def __init__(self, db_manager: DatabaseManager):
        self.db_manager = db_manager
    
    def get_random_task(self, min_points: int, max_points: int) -> Optional[Dict]:
        """Wählt zufällige Aufgabe im Punktebereich"""
        conn = self.db_manager.get_connection()
        cursor = conn.cursor()
        
        # Erst nach neuen Aufgaben suchen
        cursor.execute('''
            SELECT 
                w.semester,
                w.sheet_number,
                t.id,
                t.task_number,
                t.total_points,
                t.times_done,
                GROUP_CONCAT(s.id || ':' || s.subtask_name || ':' || s.points, '|') as subtasks_data
            FROM worksheets w
            JOIN tasks t ON w.id = t.worksheet_id
            JOIN subtasks s ON t.id = s.task_id
            WHERE t.total_points >= ? AND t.total_points <= ? AND t.times_done = 0
            GROUP BY t.id
        ''', (min_points, max_points))
        
        new_tasks = cursor.fetchall()
        
        if new_tasks:
            from random import choice
            task = choice(new_tasks)
        else:
            # Falls keine neuen Aufgaben -> Wiederholung
            cursor.execute('''
                SELECT 
                    w.semester,
                    w.sheet_number,
                    t.id,
                    t.task_number,
                    t.total_points,
                    t.times_done,
                    GROUP_CONCAT(s.id || ':' || s.subtask_name || ':' || s.points, '|') as subtasks_data
                FROM worksheets w
                JOIN tasks t ON w.id = t.worksheet_id
                JOIN subtasks s ON t.id = s.task_id
                WHERE t.total_points >= ? AND t.total_points <= ? AND t.times_done > 0
                GROUP BY t.id
            ''', (min_points, max_points))
            
            repeat_tasks = cursor.fetchall()
            if not repeat_tasks:
                conn.close()
                return None
            
            from random import choice
            task = choice(repeat_tasks)
        
        # Parse subtasks
        subtasks = []
        if task[6]:  # subtasks_data
            for subtask_data in task[6].split('|'):
                parts = subtask_data.split(':')
                subtasks.append({
                    'id': int(parts[0]),
                    'name': parts[1],
                    'points': int(parts[2])
                })
        
        conn.close()
        return {
            'id': task[2],
            'semester': task[0],
            'sheet_number': task[1],
            'task_number': task[3],
            'total_points': task[4],
            'times_done': task[5],
            'subtasks': subtasks,
            'is_repeat': task[5] > 0
        }
    
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
        """Gibt Anzahl der Aufgaben im Punktebereich zurück"""
        conn = self.db_manager.get_connection()
        cursor = conn.cursor()
        
        # Gesamtanzahl der Aufgaben im Punktebereich
        cursor.execute('''
            SELECT COUNT(*) 
            FROM tasks 
            WHERE total_points >= ? AND total_points <= ?
        ''', (min_points, max_points))
        
        total_tasks = cursor.fetchone()[0]
        
        # Anzahl der erledigten Aufgaben (times_done > 0)
        cursor.execute('''
            SELECT COUNT(*) 
            FROM tasks 
            WHERE total_points >= ? AND total_points <= ? AND times_done > 0
        ''', (min_points, max_points))
        
        completed_tasks = cursor.fetchone()[0]
        
        conn.close()
        
        return {
            'total': total_tasks,
            'completed': completed_tasks,
            'remaining': total_tasks - completed_tasks
        }


class AttemptRepository:
    def __init__(self, db_manager: DatabaseManager):
        self.db_manager = db_manager
    
    def create_attempt(self, task_id: int) -> int:
        """Erstellt einen neuen Lösungsversuch"""
        conn = self.db_manager.get_connection()
        cursor = conn.cursor()
        
        cursor.execute('''
            INSERT INTO solution_attempts (task_id, attempt_date)
            VALUES (?, ?)
        ''', (task_id, date.today()))
        
        attempt_id = cursor.lastrowid
        if attempt_id is None:
            conn.close()
            raise RuntimeError("Failed to create solution attempt - no ID returned")
        
        conn.commit()
        conn.close()
        
        return attempt_id
    
    def update_attempt_time(self, attempt_id: int, total_time: int):
        """Aktualisiert die Gesamtzeit eines Versuchs"""
        conn = self.db_manager.get_connection()
        cursor = conn.cursor()
        
        cursor.execute('''
            UPDATE solution_attempts 
            SET total_time_seconds = ?
            WHERE id = ?
        ''', (total_time, attempt_id))
        
        conn.commit()
        conn.close()
    

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
