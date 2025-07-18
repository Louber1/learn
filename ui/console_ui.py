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
        
        # Zeige Aufgaben-Statistiken für den gewählten Punktebereich
        if task_counts and point_range:
            min_points, max_points = point_range
            if min_points == max_points:
                range_text = f"{min_points}P"
            else:
                range_text = f"{min_points}-{max_points}P"
            print(f"   📊 Punktebereich {range_text}: {task_counts['completed']}/{task_counts['total']} erledigt ({task_counts['remaining']} offen)")
        
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
                print("❌ Aufgabe abgebrochen")
                self.task_service.current_attempt_id = None
        else:
            print("❌ Aufgabe abgebrochen")
            self.task_service.current_attempt_id = None
    
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
    
    def get_point_range(self) -> Optional[tuple[int, int]]:
        """Fragt Punktebereich ab"""
        try:
            min_points = int(get_simple_input("Minimale Punktzahl: "))
            max_points = int(get_simple_input("Maximale Punktzahl: "))
            return min_points, max_points
        except ValueError:
            print("❌ Bitte gültige Zahlen eingeben!")
            return None
