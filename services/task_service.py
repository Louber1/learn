from typing import Dict, Optional, List
from database.models import DatabaseManager, TaskRepository, AttemptRepository
from timer.timer import LiveTimer
from utils.keyboard import KeyboardListener, format_time

class TaskService:
    def __init__(self, db_manager: DatabaseManager):
        self.db_manager = db_manager
        self.task_repo = TaskRepository(db_manager)
        self.attempt_repo = AttemptRepository(db_manager)
        self.current_attempt_id: Optional[int] = None
        self.current_timer: Optional[LiveTimer] = None
    
    def get_random_task(self, min_points: int, max_points: int) -> Optional[Dict]:
        """Wählt zufällige Aufgabe im Punktebereich"""
        return self.task_repo.get_random_task(min_points, max_points)
    
    def get_task_counts_by_point_range(self, min_points: int, max_points: int) -> Dict[str, int]:
        """Gibt Anzahl der Aufgaben im Punktebereich zurück"""
        return self.task_repo.get_task_counts_by_point_range(min_points, max_points)
    
    def start_attempt(self, task_id: int) -> int:
        """Startet einen neuen Lösungsversuch"""
        self.current_attempt_id = self.attempt_repo.create_attempt(task_id)
        print(f"⏱️  Lösungsversuch gestartet (ID: {self.current_attempt_id})")
        return self.current_attempt_id
    
    def time_task_interactive(self, task: Dict) -> Optional[int]:
        """Interaktive Zeitmessung für die gesamte Aufgabe"""
        print(f"\n🎯 Aufgabe: {task['task_number']} ({task['total_points']} Punkte)")
        print("📝 Teilaufgaben:")
        for i, subtask in enumerate(task['subtasks'], 1):
            print(f"   {i}. {subtask['name']} ({subtask['points']}P)")
        
        print("\n⏱️  Timer-Steuerung:")
        print("   - [Enter] = Timer starten/stoppen")
        print("   - [Leertaste] = Pause/Fortsetzen")
        print("   - [q] = Abbrechen")
        
        input("\n   [Enter] zum Starten der Zeitmessung...")
        
        self.current_timer = LiveTimer()
        self.current_timer.start()
        
        print("\n   💡 Timer läuft! Arbeite an allen Teilaufgaben:")
        print("   - [Enter] = Timer stoppen und Aufgabe beenden")
        print("   - [Leertaste] = Pause/Resume")
        print("   - [q] = Abbrechen")
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
        
        # Speichere nur die Gesamtzeit
        self.attempt_repo.update_attempt_time(self.current_attempt_id, total_time)
        self.task_repo.mark_task_done(task_id)
        
        print(f"\n✅ Aufgabe abgeschlossen! Gesamtzeit: {format_time(total_time)}")
        
        # Reset für nächste Aufgabe
        self.current_attempt_id = None
    
    def get_statistics(self, task_id: Optional[int] = None) -> List:
        """Holt Zeitstatistiken"""
        return self.attempt_repo.get_statistics(task_id)
