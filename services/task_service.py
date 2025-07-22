from typing import Dict, Optional, List
from database.models import DatabaseManager, TaskRepository, AttemptRepository
from timer.timer import LiveTimer
from utils.keyboard import KeyboardListener, format_time

class TaskService:
    def __init__(self, db_manager: DatabaseManager, exam_id: Optional[int] = None):
        self.db_manager = db_manager
        self.exam_id = exam_id
        self.task_repo = TaskRepository(db_manager, exam_id)
        self.attempt_repo = AttemptRepository(db_manager)
        self.current_attempt_id: Optional[int] = None
        self.current_timer: Optional[LiveTimer] = None
    
    def set_exam_id(self, exam_id: int):
        """Sets the current exam ID for filtering tasks"""
        self.exam_id = exam_id
        self.task_repo.set_exam_id(exam_id)
    
    def get_current_exam_info(self) -> Optional[Dict]:
        """Gets information about the currently selected exam"""
        if not self.exam_id:
            return None
        
        conn = self.db_manager.get_connection()
        cursor = conn.cursor()
        
        cursor.execute('''
            SELECT id, name, description, created_at
            FROM exams
            WHERE id = ?
        ''', (self.exam_id,))
        
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
    
    def get_random_task(self, min_points: int, max_points: int) -> Optional[Dict]:
        """Wählt zufällige Aufgabe im Punktebereich"""
        return self.task_repo.get_random_task(min_points, max_points)
    
    def get_task_counts_by_point_range(self, min_points: int, max_points: int) -> Dict[str, int]:
        """Gibt Anzahl der Aufgaben im Punktebereich zurück"""
        return self.task_repo.get_task_counts_by_point_range(min_points, max_points)
    
    def start_attempt(self, task_id: int) -> int:
        """Startet einen neuen Lösungsversuch"""
        self.current_attempt_id = self.attempt_repo.create_attempt(task_id, 'in_progress')
        print(f"⏱️  Lösungsversuch gestartet (ID: {self.current_attempt_id})")
        return self.current_attempt_id
    
    def resume_attempt(self, attempt_id: int) -> int:
        """Setzt einen unterbrochenen Versuch fort"""
        self.current_attempt_id = attempt_id
        print(f"🔄 Lösungsversuch fortgesetzt (ID: {self.current_attempt_id})")
        return self.current_attempt_id
    
    def _auto_save_callback(self, current_time: int):
        """Callback für Auto-Save während Timer läuft"""
        if self.current_attempt_id:
            self.attempt_repo.auto_save_progress(self.current_attempt_id, current_time)
    
    def time_task_interactive(self, task: Dict, resume_from_seconds: int = 0) -> Optional[int]:
        """Interaktive Zeitmessung für die gesamte Aufgabe"""
        print(f"\n🎯 Aufgabe: {task['task_number']} ({task['total_points']} Punkte)")
        print("📝 Teilaufgaben:")
        for i, subtask in enumerate(task['subtasks'], 1):
            print(f"   {i}. {subtask['name']} ({subtask['points']}P)")
        
        if resume_from_seconds > 0:
            print(f"\n🔄 Fortsetzen von vorheriger Zeit: {format_time(resume_from_seconds)}")
        
        print("\n⏱️  Timer-Steuerung:")
        print("   - [Enter] = Timer starten/stoppen")
        print("   - [Leertaste] = Pause/Fortsetzen")
        print("   - [q] = Abbrechen")
        
        input("\n   [Enter] zum Starten der Zeitmessung...")
        
        # Timer mit Auto-Save und optionaler Fortsetzung
        self.current_timer = LiveTimer(
            auto_save_callback=self._auto_save_callback,
            auto_save_interval=30
        )
        self.current_timer.start(resume_from_seconds)
        
        print("\n   💡 Timer läuft! Arbeite an allen Teilaufgaben:")
        print("   - [Enter] = Timer stoppen und Aufgabe beenden")
        print("   - [Leertaste] = Pause/Resume")
        print("   - [q] = Abbrechen")
        print("   - 💾 = Auto-Save alle 30 Sekunden")
        print()
        
        try:
            with KeyboardListener() as kb:
                if not kb.available:
                    # Fallback für Systeme ohne termios
                    print("   [Enter] zum Stoppen...")
                    input()
                    duration = self.current_timer.stop()
                else:
                    # Vollständige Steuerung
                    while self.current_timer.is_running:
                        key = kb.get_key()
                        
                        if key == '\r' or key == '\n':  # Enter
                            break
                        elif key == ' ':  # Leertaste
                            if self.current_timer.is_paused:
                                self.current_timer.resume()
                            else:
                                self.current_timer.pause()
                        elif key == 'q':  # Quit
                            self.current_timer.stop()
                            print("\n   ❌ Aufgabe abgebrochen")
                            self.current_timer = None
                            return None
                            
                        import time
                        time.sleep(0.1)
                    
                    duration = self.current_timer.stop()
                    
        except KeyboardInterrupt:
            if self.current_timer:
                self.current_timer.stop()
            print("\n   ❌ Timer unterbrochen")
            self.current_timer = None
            return None
        
        print(f"\n   ✅ Aufgabe beendet! Gesamtzeit: {format_time(duration)}")
        self.current_timer = None
        return duration
    
    def complete_attempt(self, task_id: int, total_time: int):
        """Schließt den Lösungsversuch ab und speichert die Gesamtzeit"""
        if not self.current_attempt_id:
            print("❌ Kein aktiver Lösungsversuch!")
            return
        
        # Aktualisiere Status und Zeit
        self.attempt_repo.update_attempt_status(self.current_attempt_id, 'completed', total_time)
        self.task_repo.mark_task_done(task_id)
        
        print(f"\n✅ Aufgabe abgeschlossen! Gesamtzeit: {format_time(total_time)}")
        
        # Reset für nächste Aufgabe
        self.current_attempt_id = None
    
    def cancel_attempt(self):
        """Bricht den aktuellen Versuch ab"""
        if not self.current_attempt_id:
            return
        
        # Markiere als abgebrochen
        self.attempt_repo.update_attempt_status(self.current_attempt_id, 'cancelled')
        print("❌ Lösungsversuch abgebrochen")
        
        # Reset
        self.current_attempt_id = None
    
    def get_incomplete_attempts(self) -> List[Dict]:
        """Holt unvollständige Versuche für Recovery"""
        return self.attempt_repo.get_incomplete_attempts()
    
    def get_task_by_attempt(self, attempt_id: int) -> Optional[Dict]:
        """Holt Task-Informationen für einen Versuch"""
        return self.attempt_repo.get_task_by_attempt(attempt_id)
    
    def get_statistics(self, task_id: Optional[int] = None) -> List:
        """Holt Zeitstatistiken"""
        return self.attempt_repo.get_statistics(task_id)
