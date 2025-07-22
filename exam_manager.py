from typing import List, Dict, Optional
from database.models import DatabaseManager

class ExamManager:
    def __init__(self, db_manager: DatabaseManager):
        self.db_manager = db_manager
    
    def list_exams(self) -> List[Dict]:
        """Lists all available exams"""
        conn = self.db_manager.get_connection()
        cursor = conn.cursor()
        
        cursor.execute('''
            SELECT 
                e.id,
                e.name,
                e.description,
                e.created_at,
                COUNT(w.id) as worksheet_count,
                COUNT(DISTINCT t.id) as task_count
            FROM exams e
            LEFT JOIN worksheets w ON e.id = w.exam_id
            LEFT JOIN tasks t ON w.id = t.worksheet_id
            GROUP BY e.id, e.name, e.description, e.created_at
            ORDER BY e.created_at
        ''')
        
        results = cursor.fetchall()
        conn.close()
        
        exams = []
        for row in results:
            exams.append({
                'id': row[0],
                'name': row[1],
                'description': row[2],
                'created_at': row[3],
                'worksheet_count': row[4],
                'task_count': row[5]
            })
        
        return exams
    
    def get_exam_by_name(self, name: str) -> Optional[Dict]:
        """Gets exam by name"""
        conn = self.db_manager.get_connection()
        cursor = conn.cursor()
        
        cursor.execute('''
            SELECT id, name, description, created_at
            FROM exams
            WHERE name = ?
        ''', (name,))
        
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
    
    def get_exam_by_id(self, exam_id: int) -> Optional[Dict]:
        """Gets exam by ID"""
        conn = self.db_manager.get_connection()
        cursor = conn.cursor()
        
        cursor.execute('''
            SELECT id, name, description, created_at
            FROM exams
            WHERE id = ?
        ''', (exam_id,))
        
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
    
    def create_exam(self, name: str, description: Optional[str] = None) -> int:
        """Creates a new exam (used internally by import system)"""
        conn = self.db_manager.get_connection()
        cursor = conn.cursor()
        
        try:
            cursor.execute('''
                INSERT INTO exams (name, description)
                VALUES (?, ?)
            ''', (name, description))
            
            exam_id = cursor.lastrowid
            if exam_id is None:
                raise RuntimeError("Failed to create exam - no ID returned")
            
            conn.commit()
            return exam_id
            
        except Exception as e:
            conn.rollback()
            raise
        finally:
            conn.close()
    
    def delete_exam(self, exam_id: int) -> bool:
        """Deletes an exam and all its associated data"""
        conn = self.db_manager.get_connection()
        cursor = conn.cursor()
        
        try:
            # First, get exam info for confirmation
            cursor.execute('SELECT name FROM exams WHERE id = ?', (exam_id,))
            result = cursor.fetchone()
            if not result:
                print(f"❌ Exam with ID {exam_id} not found")
                return False
            
            exam_name = result[0]
            
            # Count associated data
            cursor.execute('''
                SELECT 
                    COUNT(DISTINCT w.id) as worksheets,
                    COUNT(DISTINCT t.id) as tasks,
                    COUNT(DISTINCT s.id) as subtasks,
                    COUNT(DISTINCT sa.id) as attempts
                FROM exams e
                LEFT JOIN worksheets w ON e.id = w.exam_id
                LEFT JOIN tasks t ON w.id = t.worksheet_id
                LEFT JOIN subtasks s ON t.id = s.task_id
                LEFT JOIN solution_attempts sa ON t.id = sa.task_id
                WHERE e.id = ?
            ''', (exam_id,))
            
            counts = cursor.fetchone()
            
            print(f"⚠️  This will delete exam '{exam_name}' and:")
            print(f"   📝 {counts[0]} worksheets")
            print(f"   📄 {counts[1]} tasks")
            print(f"   📋 {counts[2]} subtasks")
            print(f"   ⏱️  {counts[3]} solution attempts")
            
            confirm = input("\nAre you sure? This cannot be undone! (type 'DELETE' to confirm): ")
            if confirm != 'DELETE':
                print("❌ Deletion cancelled")
                return False
            
            # Delete in correct order (foreign key constraints)
            cursor.execute('''
                DELETE FROM solution_attempts 
                WHERE task_id IN (
                    SELECT t.id FROM tasks t
                    JOIN worksheets w ON t.worksheet_id = w.id
                    WHERE w.exam_id = ?
                )
            ''', (exam_id,))
            
            cursor.execute('''
                DELETE FROM subtasks 
                WHERE task_id IN (
                    SELECT t.id FROM tasks t
                    JOIN worksheets w ON t.worksheet_id = w.id
                    WHERE w.exam_id = ?
                )
            ''', (exam_id,))
            
            cursor.execute('''
                DELETE FROM tasks 
                WHERE worksheet_id IN (
                    SELECT id FROM worksheets WHERE exam_id = ?
                )
            ''', (exam_id,))
            
            cursor.execute('DELETE FROM worksheets WHERE exam_id = ?', (exam_id,))
            cursor.execute('DELETE FROM exams WHERE id = ?', (exam_id,))
            
            conn.commit()
            print(f"✅ Exam '{exam_name}' deleted successfully")
            return True
            
        except Exception as e:
            conn.rollback()
            print(f"❌ Failed to delete exam: {e}")
            raise
        finally:
            conn.close()


def main():
    """Simple CLI for exam management (list and delete only)"""
    print("=== 📋 Simplified Exam Manager ===")
    print("💡 Note: Use 'python import_data.py <csv_file>' to import exams")
    
    # Initialize database manager
    db_manager = DatabaseManager()
    db_manager.init_database()
    
    exam_manager = ExamManager(db_manager)
    
    while True:
        print("\n" + "="*50)
        print("1. List all exams")
        print("2. Delete exam")
        print("3. Exit")
        
        choice = input("\nChoice: ").strip()
        
        if choice == '1':
            exams = exam_manager.list_exams()
            if not exams:
                print("📋 No exams found")
                print("💡 Import exams using: python import_data.py <csv_file>")
            else:
                print(f"\n📊 Available Exams:")
                for exam in exams:
                    print(f"   📋 {exam['name']} (ID: {exam['id']})")
                    print(f"      Description: {exam['description'] or 'None'}")
                    print(f"      Created: {exam['created_at']}")
                    print(f"      Worksheets: {exam['worksheet_count']}")
                    print(f"      Tasks: {exam['task_count']}")
                    print()
        
        elif choice == '2':
            exams = exam_manager.list_exams()
            if not exams:
                print("📋 No exams to delete")
                continue
            
            print("\nAvailable exams:")
            for exam in exams:
                print(f"   {exam['id']}: {exam['name']}")
            
            try:
                exam_id = int(input("\nEnter exam ID to delete: ").strip())
                exam_manager.delete_exam(exam_id)
            except ValueError:
                print("❌ Invalid exam ID")
            except Exception as e:
                print(f"❌ Failed to delete exam: {e}")
        
        elif choice == '3':
            print("👋 Goodbye!")
            break
        
        else:
            print("❌ Invalid choice!")


if __name__ == "__main__":
    main()
