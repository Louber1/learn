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
        self.subtask_times: Dict[int, int] = {}
    
    def get_random_task(self, min_points: int, max_points: int) -> Optional[Dict]:
        """Wählt zufällige Aufgabe im Punktebereich"""
        return self.task_repo.get_random_task(min_points, max_points)
    
    def start_attempt(self, task_id: int) -> int:
        """Startet einen neuen Lösungsversuch"""
        self.current_attempt_id = self.attempt_repo.create_attempt(task_id)
        self.subtask_times = {}
        print(f"⏱️  Lösungsversuch gestartet (ID: {self.current_attempt_id})")
        return self.current_attempt_id
    
    def time_subtask_interactive(self, subtask: Dict) -> Optional[int]:
        """Interaktive Zeitmessung mit Live-Timer und Pause-Funktion"""
        print(f"\n📝 Teilaufgabe: {subtask['name']} ({subtask['points']} Punkte)")
        print("   Steuerung:")
        print("   - [Enter] = Timer starten/stoppen")
        print("   - [Leertaste] = Pause/Fortsetzen")
        print("   - [q] = Abbrechen")
        
        input("\n   [Enter] zum Starten...")
        
        timer = LiveTimer()
        timer.start()
        
        print("   💡 Während der Timer läuft:")
        print("   - [Enter] = Stoppen")
        print("   - [Leertaste] = Pause/Resume")
        print("   - [q] = Abbrechen")
        print()
        
        try:
            with KeyboardListener() as kb:
                if not kb.available:
                    # Fallback für Systeme ohne termios
                    print("   [Enter] zum Stoppen...")
                    input()
                    duration = timer.stop()
                else:
                    # Vollständige Steuerung
                    while timer.is_running:
                        key = kb.get_key()
                        
                        if key == '\r' or key == '\n':  # Enter
                            break
                        elif key == ' ':  # Leertaste
                            if timer.is_paused:
                                timer.resume()
                            else:
                                timer.pause()
                        elif key == 'q':  # Quit
                            timer.stop()
                            print("\n   ❌ Teilaufgabe abgebrochen")
                            return None
                            
                        import time
                        time.sleep(0.1)
                    
                    duration = timer.stop()
                    
        except KeyboardInterrupt:
            timer.stop()
            print("\n   ❌ Timer unterbrochen")
            return None
        
        print(f"\n   ✅ Teilaufgabe beendet! Zeit: {format_time(duration)}")
        
        # Speichere Zeit
        self.subtask_times[subtask['id']] = duration
        
        return duration
    
    def complete_attempt(self, task_id: int):
        """Schließt den Lösungsversuch ab und speichert alle Daten"""
        if not self.current_attempt_id:
            print("❌ Kein aktiver Lösungsversuch!")
            return
        
        total_time = sum(self.subtask_times.values())
        
        # Speichere Daten
        self.attempt_repo.update_attempt_time(self.current_attempt_id, total_time)
        
        for subtask_id, time_sec in self.subtask_times.items():
            self.attempt_repo.save_subtask_time(self.current_attempt_id, subtask_id, time_sec)
        
        self.task_repo.mark_task_done(task_id)
        
        print(f"\n✅ Aufgabe abgeschlossen! Gesamtzeit: {format_time(total_time)}")
        
        # Zeige Teilaufgaben-Aufschlüsselung
        if len(self.subtask_times) > 1:
            print("\n📊 Zeitaufschlüsselung:")
            for subtask_id, time_sec in self.subtask_times.items():
                print(f"   Teilaufgabe {subtask_id}: {format_time(time_sec)}")
        
        # Reset für nächste Aufgabe
        self.current_attempt_id = None
        self.subtask_times = {}
    
    def get_statistics(self, task_id: Optional[int] = None) -> List:
        """Holt Zeitstatistiken"""
        return self.attempt_repo.get_statistics(task_id)
