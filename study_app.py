import sqlite3
import random
from datetime import datetime

class StudyApp:
    def __init__(self, db_path="physics_tasks.db"):
        self.db_path = db_path
    
    def get_connection(self):
        return sqlite3.connect(self.db_path)
    
    def get_random_task(self, min_points, max_points):
        """Wählt zufällige Aufgabe im Punktebereich"""
        conn = self.get_connection()
        cursor = conn.cursor()
        
        # Erst nach neuen Aufgaben suchen (times_done = 0)
        cursor.execute('''
            SELECT 
                w.semester,
                w.sheet_number,
                t.id,
                t.task_number,
                t.total_points,
                t.times_done,
                GROUP_CONCAT(s.subtask_name || ' (' || s.points || 'P)', ', ') as subtasks
            FROM worksheets w
            JOIN tasks t ON w.id = t.worksheet_id
            JOIN subtasks s ON t.id = s.task_id
            WHERE t.total_points >= ? AND t.total_points <= ? AND t.times_done = 0
            GROUP BY t.id
        ''', (min_points, max_points))
        
        new_tasks = cursor.fetchall()
        
        if new_tasks:
            task = random.choice(new_tasks)
            conn.close()
            return {
                'id': task[2],
                'semester': task[0],
                'sheet_number': task[1],
                'task_number': task[3],
                'total_points': task[4],
                'times_done': task[5],
                'subtasks': task[6],
                'is_repeat': False
            }
        
        # Falls keine neuen Aufgaben -> Wiederholung
        cursor.execute('''
            SELECT 
                w.semester,
                w.sheet_number,
                t.id,
                t.task_number,
                t.total_points,
                t.times_done,
                GROUP_CONCAT(s.subtask_name || ' (' || s.points || 'P)', ', ') as subtasks
            FROM worksheets w
            JOIN tasks t ON w.id = t.worksheet_id
            JOIN subtasks s ON t.id = s.task_id
            WHERE t.total_points >= ? AND t.total_points <= ? AND t.times_done > 0
            GROUP BY t.id
        ''', (min_points, max_points))
        
        repeat_tasks = cursor.fetchall()
        conn.close()
        
        if repeat_tasks:
            task = random.choice(repeat_tasks)
            return {
                'id': task[2],
                'semester': task[0],
                'sheet_number': task[1],
                'task_number': task[3],
                'total_points': task[4],
                'times_done': task[5],
                'subtasks': task[6],
                'is_repeat': True
            }
        
        return None
    
    def mark_task_done(self, task_id):
        """Markiert Aufgabe als erledigt"""
        conn = self.get_connection()
        cursor = conn.cursor()
        
        cursor.execute('''
            UPDATE tasks 
            SET times_done = times_done + 1
            WHERE id = ?
        ''', (task_id,))
        
        conn.commit()
        conn.close()
    
    def show_progress(self, min_points, max_points):
        """Zeigt Fortschritt im Punktebereich"""
        conn = self.get_connection()
        cursor = conn.cursor()
        
        cursor.execute('''
            SELECT 
                COUNT(*) as total,
                SUM(CASE WHEN times_done = 0 THEN 1 ELSE 0 END) as new_tasks,
                SUM(CASE WHEN times_done > 0 THEN 1 ELSE 0 END) as done_tasks,
                AVG(CAST(times_done AS FLOAT)) as avg_repetitions
            FROM tasks
            WHERE total_points >= ? AND total_points <= ?
        ''', (min_points, max_points))
        
        result = cursor.fetchone()
        conn.close()
        
        total, new_tasks, done_tasks, avg_reps = result
        
        print(f"\n📊 Fortschritt ({min_points}-{max_points} Punkte):")
        print(f"   🆕 Noch offen: {new_tasks} Aufgaben")
        print(f"   ✅ Bereits gemacht: {done_tasks} Aufgaben")
        print(f"   📈 Gesamt: {total} Aufgaben")
        if avg_reps:
            print(f"   🔄 Durchschnittliche Wiederholungen: {avg_reps:.1f}")
        
        if new_tasks == 0 and done_tasks > 0:
            print("   🎉 Alle Aufgaben einmal bearbeitet - jetzt Wiederholung!")
    
    def display_task(self, task):
        """Zeigt Aufgabe formatiert an"""
        if task is None:
            print("❌ Keine Aufgaben im gewählten Punktebereich gefunden!")
            return
        
        if task['is_repeat']:
            print("🔄 Wiederholung:")
        else:
            print("📄 Neue Aufgabe:")
        
        print(f"   Semester: {task['semester']}")
        print(f"   Blatt: {task['sheet_number']}")
        print(f"   Aufgabe: {task['task_number']}")
        print(f"   Punkte: {task['total_points']}")
        print(f"   Teilaufgaben: {task['subtasks']}")
        
        if task['is_repeat']:
            print(f"   (Bereits {task['times_done']}x bearbeitet)")

def main():
    app = StudyApp()
    
    print("=== 🎓 ExPhys Lernassistent ===")
    
    while True:
        print("\n" + "="*50)
        try:
            min_points = int(input("Minimale Punktzahl: "))
            max_points = int(input("Maximale Punktzahl: "))
            
            app.show_progress(min_points, max_points)
            
            print("\n[Enter] für zufällige Aufgabe, [q] zum Beenden:")
            choice = input().strip().lower()
            
            if choice == 'q':
                break
            
            task = app.get_random_task(min_points, max_points)
            app.display_task(task)
            
            if task:
                print("\n[Enter] wenn erledigt, [s] zum Überspringen:")
                done = input().strip().lower()
                
                if done != 's':
                    app.mark_task_done(task['id'])
                    print("✅ Aufgabe als erledigt markiert!")
        
        except ValueError:
            print("❌ Bitte gültige Zahlen eingeben!")
        except KeyboardInterrupt:
            print("\n\n👋 Auf Wiedersehen!")
            break

if __name__ == "__main__":
    main()