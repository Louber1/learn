from database.models import DatabaseManager
from services.task_service import TaskService
from ui.console_ui import ConsoleUI
from utils.keyboard import get_simple_input
from exam_manager import ExamManager

def select_exam(db_manager: DatabaseManager) -> int:
    """Allows user to select an exam"""
    exam_manager = ExamManager(db_manager)
    exams = exam_manager.list_exams()
    
    if not exams:
        print("❌ No exams found! Please run the migration script first or add exams using exam_manager.py")
        exit(1)
    
    if len(exams) == 1:
        exam = exams[0]
        print(f"📋 Using exam: {exam['name']}")
        return exam['id']
    
    print("\n📋 Available Exams:")
    for i, exam in enumerate(exams, 1):
        print(f"   {i}. {exam['name']}")
        if exam['description']:
            print(f"      {exam['description']}")
        print(f"      Tasks: {exam['task_count']}")
        print()
    
    while True:
        try:
            choice = int(get_simple_input("Select exam (number): ").strip())
            if 1 <= choice <= len(exams):
                selected_exam = exams[choice - 1]
                print(f"✅ Selected: {selected_exam['name']}")
                return selected_exam['id']
            else:
                print(f"❌ Please enter a number between 1 and {len(exams)}")
        except ValueError:
            print("❌ Please enter a valid number")

def main():
    # Initialisierung
    db_manager = DatabaseManager()
    db_manager.init_database()
    
    # Select exam
    exam_id = select_exam(db_manager)
    
    task_service = TaskService(db_manager, exam_id)
    ui = ConsoleUI(task_service)
    
    # Show current exam info
    exam_info = task_service.get_current_exam_info()
    
    print("=== Lernassistent ===")
    if exam_info:
        print(f"📋 Current Exam: {exam_info['name']}")
        if exam_info['description']:
            print(f"   Description: {exam_info['description']}")
    
    # Prüfe auf unterbrochene Sessions
    recovery_handled = ui.show_recovery_options()
    
    while True:
        print("\n" + "="*50)
        if exam_info:
            print(f"Current Exam: {exam_info['name']}")
        print("1. Aufgabe lösen")
        print("2. Zeitstatistiken anzeigen")
        print("3. Switch exam")
        print("4. Beenden")
        
        choice = get_simple_input("\nWahl: ")
        
        if choice == '1':
            point_range = ui.get_point_range()
            if point_range is not None:
                min_points, max_points = point_range
                task = task_service.get_random_task(min_points, max_points)
                if task is not None:
                    # Hole Aufgaben-Statistiken für den gewählten Punktebereich
                    task_counts = task_service.get_task_counts_by_point_range(min_points, max_points)
                    ui.solve_task_interactive(task, task_counts, (min_points, max_points))
                else:
                    print("❌ Keine Aufgabe im gewählten Punktebereich gefunden!")
        
        elif choice == '2':
            ui.show_statistics()
        
        elif choice == '3':
            # Switch exam
            new_exam_id = select_exam(db_manager)
            task_service.set_exam_id(new_exam_id)
            exam_info = task_service.get_current_exam_info()
            print(f"✅ Switched to exam: {exam_info['name'] if exam_info else 'Unknown'}")
        
        elif choice == '4':
            print("👋 Auf Wiedersehen!")
            break
        
        else:
            print("❌ Ungültige Auswahl!")

if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        print("\n\n👋 Auf Wiedersehen!")
