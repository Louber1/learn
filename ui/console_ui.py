from typing import Dict, Optional
from services.task_service import TaskService
from utils.keyboard import get_simple_input, format_time

class ConsoleUI:
    def __init__(self, task_service: TaskService):
        self.task_service = task_service
    
    def display_task_info(self, task: Dict, task_counts: Optional[Dict[str, int]] = None, point_range: Optional[tuple[int, int]] = None):
        """Zeigt Aufgabeninformationen"""
        print(f"\n🎯 Aufgabe: Semester {task['semester']}, Blatt {task['sheet_number']}, Aufgabe {task['task_number']}")
        print(f"   Punkte: {task['total_points']}")
        print(f"   Status: {'🔄 Wiederholung' if task['is_repeat'] else '🆕 Neue Aufgabe'}")
        print(f"   Teilaufgaben: {len(task['subtasks'])}")
        
        # Zeige Aufgaben-Statistiken für den gewählten Punktebereich mit Round-Info
        if task_counts and point_range:
            min_points, max_points = point_range
            if min_points == max_points:
                range_text = f"{min_points}P"
            else:
                range_text = f"{min_points}-{max_points}P"
            
            current_round = task_counts['current_round']
            tasks_at_current_level = task_counts['tasks_at_current_level']
            total_tasks = task_counts['total']
            
            print(f"   📊 Punktebereich {range_text}: {task_counts['completed']}/{task_counts['total']} erledigt")
            print(f"   🔄 Aktuelle Runde {current_round}: {tasks_at_current_level}/{total_tasks} Aufgaben verfügbar")
            
            if current_round == 1:
                print(f"   💡 Neue Aufgaben werden bevorzugt (Round {current_round})")
            else:
                print(f"   💡 Alle Aufgaben mindestens {current_round-1}x gemacht - Round {current_round} läuft")
        
        for i, subtask in enumerate(task['subtasks'], 1):
            print(f"   {i}. {subtask['name']} ({subtask['points']}P)")
    
    def solve_task_interactive(self, task: Dict, task_counts: Optional[Dict[str, int]] = None, point_range: Optional[tuple[int, int]] = None):
        """Interaktive Aufgabenlösung mit vereinfachtem Timer"""
        if not task:
            print("❌ Keine Aufgabe verfügbar!")
            return
        
        self.display_task_info(task, task_counts, point_range)
        
        choice = get_simple_input("\n[Enter] zum Starten, [s] zum Überspringen: ").lower()
        if choice == 's':
            return
        
        # Starte Lösungsversuch
        self.task_service.start_attempt(task['id'])
        
        # Starte Timer für die gesamte Aufgabe
        total_time = self.task_service.time_task_interactive(task)
        
        if total_time is not None:
            # Frage ob Aufgabe als erledigt markiert werden soll
            finish_choice = get_simple_input("\n[Enter] um Aufgabe als erledigt zu markieren, [c] zum Abbrechen: ").lower()
            if finish_choice != 'c':
                self.task_service.complete_attempt(task['id'], total_time)
            else:
                self.task_service.cancel_attempt()
        else:
            self.task_service.cancel_attempt()
    
    def resume_task_interactive(self, task: Dict, attempt_data: Dict):
        """Setzt eine unterbrochene Aufgabe fort"""
        self.display_task_info(task)
        
        elapsed_time = attempt_data['elapsed_time']
        print(f"\n🔄 Unterbrochene Session gefunden!")
        print(f"   Bisherige Zeit: {format_time(elapsed_time)}")
        print(f"   Letzte Aktivität: {attempt_data['last_updated']}")
        
        choice = get_simple_input("\n[Enter] zum Fortsetzen, [n] für neue Session, [d] zum Löschen: ").lower()
        
        if choice == 'd':
            # Markiere als abgebrochen
            self.task_service.attempt_repo.update_attempt_status(attempt_data['attempt_id'], 'cancelled')
            print("❌ Unterbrochene Session gelöscht")
            return
        elif choice == 'n':
            # Neue Session starten
            self.task_service.start_attempt(task['id'])
            total_time = self.task_service.time_task_interactive(task)
        else:
            # Session fortsetzen
            self.task_service.resume_attempt(attempt_data['attempt_id'])
            total_time = self.task_service.time_task_interactive(task, elapsed_time)
        
        if total_time is not None:
            finish_choice = get_simple_input("\n[Enter] um Aufgabe als erledigt zu markieren, [c] zum Abbrechen: ").lower()
            if finish_choice != 'c':
                self.task_service.complete_attempt(task['id'], total_time)
            else:
                self.task_service.cancel_attempt()
        else:
            self.task_service.cancel_attempt()
    
    def show_statistics(self):
        """Zeigt Zeitstatistiken"""
        results = self.task_service.get_statistics()
        
        if not results:
            print("📊 Noch keine Zeitdaten verfügbar")
            return
        
        print(f"\n📊 Top 10 Aufgaben nach Häufigkeit:")
        print(f"{'Aufgabe':<20} {'Versuche':<8} {'⌀ Zeit':<8} {'🏆 Beste':<8} {'😰 Schlechteste':<8}")
        print("-" * 60)
        
        for row in results:
            avg_time = format_time(int(row[2])) if row[2] else "N/A"
            best_time = format_time(int(row[3])) if row[3] else "N/A"
            worst_time = format_time(int(row[4])) if row[4] else "N/A"
            print(f"{row[0]:<20} {row[1]:<8} {avg_time:<8} {best_time:<8} {worst_time:<8}")
    
    def show_recovery_options(self) -> bool:
        """Zeigt Recovery-Optionen für unterbrochene Sessions"""
        incomplete_attempts = self.task_service.get_incomplete_attempts()
        
        if not incomplete_attempts:
            return False
        
        print("\n🔄 Unterbrochene Sessions gefunden:")
        print("-" * 50)
        
        for i, attempt in enumerate(incomplete_attempts, 1):
            elapsed_time = format_time(attempt['elapsed_time'])
            print(f"{i}. {attempt['task_info']} ({attempt['total_points']}P)")
            print(f"   Zeit: {elapsed_time} | Datum: {attempt['attempt_date']}")
            print(f"   Letzte Aktivität: {attempt['last_updated']}")
            print()
        
        print("Optionen:")
        print("1-{}: Session fortsetzen".format(len(incomplete_attempts)))
        print("a: Alle Sessions löschen")
        print("Enter: Überspringen und normal fortfahren")
        
        choice = get_simple_input("\nWahl: ").lower()
        
        if choice == 'a':
            # Alle als abgebrochen markieren
            for attempt in incomplete_attempts:
                self.task_service.attempt_repo.update_attempt_status(
                    attempt['attempt_id'], 'cancelled'
                )
            print("✅ Alle unterbrochenen Sessions gelöscht")
            return True
        
        try:
            choice_num = int(choice)
            if 1 <= choice_num <= len(incomplete_attempts):
                # Gewählte Session fortsetzen
                attempt = incomplete_attempts[choice_num - 1]
                task = self.task_service.get_task_by_attempt(attempt['attempt_id'])
                
                if task:
                    self.resume_task_interactive(task, attempt)
                    return True
                else:
                    print("❌ Aufgabe nicht gefunden!")
        except ValueError:
            pass
        
        return False
    
    def get_point_range(self) -> Optional[tuple[int, int]]:
        """Fragt Punktebereich ab"""
        try:
            min_points = int(get_simple_input("Minimale Punktzahl: "))
            max_points = int(get_simple_input("Maximale Punktzahl: "))
            return min_points, max_points
        except ValueError:
            print("❌ Bitte gültige Zahlen eingeben!")
            return None
