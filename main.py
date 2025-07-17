from database.models import DatabaseManager
from services.task_service import TaskService
from ui.console_ui import ConsoleUI
from utils.keyboard import get_simple_input

def main():
    # Initialisierung
    db_manager = DatabaseManager()
    db_manager.init_database()
    
    task_service = TaskService(db_manager)
    ui = ConsoleUI(task_service)
    
    print("=== ⏱️  ExPhys Lernassistent mit Live-Timer ===")
    print("💡 Features:")
    print("   - Live-Timer mit Sekunden-Anzeige")
    print("   - Pause/Resume-Funktion")
    print("   - Einzelne Zeitmessung pro Teilaufgabe")
    print("   - Detaillierte Statistiken")
    
    while True:
        print("\n" + "="*50)
        print("1. Aufgabe lösen")
        print("2. Zeitstatistiken anzeigen")
        print("3. Beenden")
        
        choice = get_simple_input("\nWahl: ")
        
        if choice == '1':
            point_range = ui.get_point_range()
            if point_range is not None:
                min_points, max_points = point_range
                task = task_service.get_random_task(min_points, max_points)
                if task is not None:
                    ui.solve_task_interactive(task)
                else:
                    print("❌ Keine Aufgabe im gewählten Punktebereich gefunden!")
        
        elif choice == '2':
            ui.show_statistics()
        
        elif choice == '3':
            print("👋 Auf Wiedersehen!")
            break
        
        else:
            print("❌ Ungültige Auswahl!")

if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        print("\n\n👋 Auf Wiedersehen!")
