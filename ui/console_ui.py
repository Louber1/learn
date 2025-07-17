from typing import Dict, Optional
from services.task_service import TaskService
from utils.keyboard import get_simple_input, format_time

class ConsoleUI:
    def __init__(self, task_service: TaskService):
        self.task_service = task_service
    
    def display_task_info(self, task: Dict):
        """Zeigt Aufgabeninformationen"""
        print(f"\n🎯 Aufgabe: Semester {task['semester']}, Blatt {task['sheet_number']}, Aufgabe {task['task_number']}")
        print(f"   Punkte: {task['total_points']}")
        print(f"   Status: {'🔄 Wiederholung' if task['is_repeat'] else '🆕 Neue Aufgabe'}")
        print(f"   Teilaufgaben: {len(task['subtasks'])}")
        
        for i, subtask in enumerate(task['subtasks'], 1):
            print(f"   {i}. {subtask['name']} ({subtask['points']}P)")
    
    def solve_task_interactive(self, task: Dict):
        """Interaktive Aufgabenlösung"""
        if not task:
            print("❌ Keine Aufgabe verfügbar!")
            return
        
        self.display_task_info(task)
        
        choice = get_simple_input("\n[Enter] zum Starten, [s] zum Überspringen: ").lower()
        if choice == 's':
            return
        
        # Starte Lösungsversuch
        self.task_service.start_attempt(task['id'])
        
        # Gehe durch alle Teilaufgaben
        for i, subtask in enumerate(task['subtasks'], 1):
            print(f"\n{'='*50}")
            print(f"Teilaufgabe {i}/{len(task['subtasks'])}")
            
            sub_choice = get_simple_input(f"[Enter] für Timer, [s] überspringen, [q] Aufgabe beenden: ").lower()
            
            if sub_choice == 'q':
                print("❌ Aufgabe abgebrochen")
                self.task_service.current_attempt_id = None
                self.task_service.subtask_times = {}
                return
            elif sub_choice == 's':
                print("   ⏩ Teilaufgabe übersprungen")
                continue
            else:
                result = self.task_service.time_subtask_interactive(subtask)
                if result is None:  # Abgebrochen
                    continue
        
        # Abschließen
        if self.task_service.subtask_times:  # Nur wenn mindestens eine Teilaufgabe bearbeitet wurde
            finish_choice = get_simple_input("\n[Enter] um Aufgabe als erledigt zu markieren, [c] zum Abbrechen: ").lower()
            if finish_choice != 'c':
                self.task_service.complete_attempt(task['id'])
            else:
                print("❌ Aufgabe abgebrochen")
                self.task_service.current_attempt_id = None
                self.task_service.subtask_times = {}
        else:
            print("❌ Keine Teilaufgaben bearbeitet")
    
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
