#!/usr/bin/env python3
"""
Script to view all solution attempts from the physics learning system.
Shows detailed information about completed, cancelled, and in-progress attempts.
"""

from database.models import DatabaseManager
from utils.keyboard import get_simple_input
from datetime import datetime
import sqlite3
from typing import List, Dict, Optional

def format_time(seconds: Optional[int]) -> str:
    """Format seconds into readable time format"""
    if seconds is None:
        return "N/A"
    
    hours = seconds // 3600
    minutes = (seconds % 3600) // 60
    secs = seconds % 60
    
    if hours > 0:
        return f"{hours}h {minutes}m {secs}s"
    elif minutes > 0:
        return f"{minutes}m {secs}s"
    else:
        return f"{secs}s"

def format_date(date_str: str) -> str:
    """Format date string for display"""
    try:
        # Parse the date and format it nicely
        date_obj = datetime.strptime(date_str, '%Y-%m-%d')
        return date_obj.strftime('%d.%m.%Y')
    except:
        return date_str

def format_datetime(datetime_str: str) -> str:
    """Format datetime string for display"""
    if not datetime_str:
        return "N/A"
    try:
        # Handle different datetime formats
        for fmt in ['%Y-%m-%d %H:%M:%S', '%Y-%m-%d %H:%M:%S.%f']:
            try:
                dt_obj = datetime.strptime(datetime_str, fmt)
                return dt_obj.strftime('%d.%m.%Y %H:%M:%S')
            except ValueError:
                continue
        return datetime_str
    except:
        return datetime_str

class SolutionAttemptViewer:
    def __init__(self, db_manager: DatabaseManager):
        self.db_manager = db_manager
    
    def get_all_attempts(self, status_filter: Optional[str] = None, exam_id: Optional[int] = None) -> List[Dict]:
        """Get all solution attempts with task and exam information"""
        conn = self.db_manager.get_connection()
        cursor = conn.cursor()
        
        query = '''
            SELECT 
                sa.id as attempt_id,
                sa.task_id,
                sa.attempt_date,
                sa.total_time_seconds,
                sa.status,
                sa.created_at,
                sa.last_updated,
                t.task_number,
                t.total_points,
                t.times_done,
                w.semester,
                w.sheet_number,
                e.name as exam_name,
                e.id as exam_id
            FROM solution_attempts sa
            JOIN tasks t ON sa.task_id = t.id
            JOIN worksheets w ON t.worksheet_id = w.id
            LEFT JOIN exams e ON w.exam_id = e.id
        '''
        
        params = []
        conditions = []
        
        if status_filter:
            conditions.append("sa.status = ?")
            params.append(status_filter)
        
        if exam_id:
            conditions.append("w.exam_id = ?")
            params.append(exam_id)
        
        if conditions:
            query += " WHERE " + " AND ".join(conditions)
        
        query += " ORDER BY sa.created_at DESC"
        
        cursor.execute(query, params)
        results = cursor.fetchall()
        conn.close()
        
        attempts = []
        for row in results:
            attempts.append({
                'attempt_id': row[0],
                'task_id': row[1],
                'attempt_date': row[2],
                'total_time_seconds': row[3],
                'status': row[4],
                'created_at': row[5],
                'last_updated': row[6],
                'task_number': row[7],
                'total_points': row[8],
                'times_done': row[9],
                'semester': row[10],
                'sheet_number': row[11],
                'exam_name': row[12] or "Unknown Exam",
                'exam_id': row[13]
            })
        
        return attempts
    
    def get_attempt_statistics(self) -> Dict:
        """Get overall statistics about attempts"""
        conn = self.db_manager.get_connection()
        cursor = conn.cursor()
        
        # Total attempts by status
        cursor.execute('''
            SELECT status, COUNT(*) as count
            FROM solution_attempts
            GROUP BY status
        ''')
        status_counts = dict(cursor.fetchall())
        
        # Average time by status
        cursor.execute('''
            SELECT status, AVG(total_time_seconds) as avg_time, COUNT(*) as count
            FROM solution_attempts
            WHERE total_time_seconds IS NOT NULL
            GROUP BY status
        ''')
        avg_times = {}
        for row in cursor.fetchall():
            avg_times[row[0]] = {'avg_time': row[1], 'count': row[2]}
        
        # Total time spent
        cursor.execute('''
            SELECT SUM(total_time_seconds) as total_time
            FROM solution_attempts
            WHERE total_time_seconds IS NOT NULL
        ''')
        total_time = cursor.fetchone()[0] or 0
        
        # Most attempted tasks
        cursor.execute('''
            SELECT 
                PRINTF('Sem%d Bl%d Aufg%s', w.semester, w.sheet_number, t.task_number) as task_info,
                COUNT(sa.id) as attempt_count,
                AVG(sa.total_time_seconds) as avg_time,
                e.name as exam_name
            FROM solution_attempts sa
            JOIN tasks t ON sa.task_id = t.id
            JOIN worksheets w ON t.worksheet_id = w.id
            LEFT JOIN exams e ON w.exam_id = e.id
            WHERE sa.total_time_seconds IS NOT NULL
            GROUP BY t.id
            ORDER BY attempt_count DESC
            LIMIT 10
        ''')
        most_attempted = cursor.fetchall()
        
        conn.close()
        
        return {
            'status_counts': status_counts,
            'avg_times': avg_times,
            'total_time': total_time,
            'most_attempted': most_attempted
        }
    
    def get_available_exams(self) -> List[Dict]:
        """Get list of available exams"""
        conn = self.db_manager.get_connection()
        cursor = conn.cursor()
        
        cursor.execute('''
            SELECT DISTINCT e.id, e.name, COUNT(sa.id) as attempt_count
            FROM exams e
            LEFT JOIN worksheets w ON e.id = w.exam_id
            LEFT JOIN tasks t ON w.id = t.worksheet_id
            LEFT JOIN solution_attempts sa ON t.id = sa.task_id
            GROUP BY e.id, e.name
            ORDER BY e.name
        ''')
        
        results = cursor.fetchall()
        conn.close()
        
        return [{'id': row[0], 'name': row[1], 'attempt_count': row[2]} for row in results]

def display_attempts_table(attempts: List[Dict]):
    """Display attempts in a formatted table"""
    if not attempts:
        print("❌ No attempts found.")
        return
    
    print(f"\n📊 Found {len(attempts)} solution attempts:")
    print("=" * 120)
    
    # Header
    header = f"{'ID':<4} {'Date':<12} {'Exam':<15} {'Task':<12} {'Points':<6} {'Time':<10} {'Status':<12} {'Created':<19}"
    print(header)
    print("-" * 120)
    
    # Data rows
    for attempt in attempts:
        task_info = f"S{attempt['semester']}B{attempt['sheet_number']}A{attempt['task_number']}"
        exam_name = attempt['exam_name'][:14] if len(attempt['exam_name']) > 14 else attempt['exam_name']
        
        row = (f"{attempt['attempt_id']:<4} "
               f"{format_date(attempt['attempt_date']):<12} "
               f"{exam_name:<15} "
               f"{task_info:<12} "
               f"{attempt['total_points']:<6} "
               f"{format_time(attempt['total_time_seconds']):<10} "
               f"{attempt['status']:<12} "
               f"{format_datetime(attempt['created_at']):<19}")
        print(row)

def display_statistics(stats: Dict):
    """Display attempt statistics"""
    print("\n📈 Solution Attempt Statistics:")
    print("=" * 50)
    
    # Status breakdown
    print("\n🔍 Attempts by Status:")
    total_attempts = sum(stats['status_counts'].values())
    for status, count in stats['status_counts'].items():
        percentage = (count / total_attempts * 100) if total_attempts > 0 else 0
        print(f"   {status:<12}: {count:>3} ({percentage:>5.1f}%)")
    
    print(f"\n   Total Attempts: {total_attempts}")
    print(f"   Total Time Spent: {format_time(stats['total_time'])}")
    
    # Average times by status
    if stats['avg_times']:
        print("\n⏱️  Average Times by Status:")
        for status, data in stats['avg_times'].items():
            avg_time = int(data['avg_time']) if data['avg_time'] else 0
            print(f"   {status:<12}: {format_time(avg_time)} ({data['count']} attempts)")
    
    # Most attempted tasks
    if stats['most_attempted']:
        print("\n🎯 Most Attempted Tasks:")
        for i, (task_info, count, avg_time, exam_name) in enumerate(stats['most_attempted'], 1):
            avg_time_formatted = format_time(int(avg_time)) if avg_time else "N/A"
            exam_display = exam_name if exam_name else "Unknown"
            print(f"   {i:>2}. {task_info:<15} - {count} attempts, avg: {avg_time_formatted} ({exam_display})")

def main():
    # Initialize database
    db_manager = DatabaseManager()
    db_manager.init_database()
    
    viewer = SolutionAttemptViewer(db_manager)
    
    print("=== 📊 Solution Attempts Viewer ===")
    print("View and analyze all your solution attempts")
    
    while True:
        print("\n" + "="*50)
        print("1. View all attempts")
        print("2. View by status (completed/cancelled/in_progress)")
        print("3. View by exam")
        print("4. Show statistics")
        print("5. Search by task")
        print("6. Exit")
        
        choice = get_simple_input("\nSelect option: ").strip()
        
        if choice == '1':
            attempts = viewer.get_all_attempts()
            display_attempts_table(attempts)
        
        elif choice == '2':
            print("\nAvailable statuses:")
            print("1. completed")
            print("2. cancelled") 
            print("3. in_progress")
            
            status_choice = get_simple_input("Select status (1-3): ").strip()
            status_map = {'1': 'completed', '2': 'cancelled', '3': 'in_progress'}
            
            if status_choice in status_map:
                status = status_map[status_choice]
                attempts = viewer.get_all_attempts(status_filter=status)
                print(f"\n🔍 Showing {status} attempts:")
                display_attempts_table(attempts)
            else:
                print("❌ Invalid status selection!")
        
        elif choice == '3':
            exams = viewer.get_available_exams()
            if not exams:
                print("❌ No exams found!")
                continue
            
            print("\nAvailable exams:")
            for i, exam in enumerate(exams, 1):
                print(f"{i}. {exam['name']} ({exam['attempt_count']} attempts)")
            
            try:
                exam_choice = int(get_simple_input("Select exam (number): ").strip())
                if 1 <= exam_choice <= len(exams):
                    selected_exam = exams[exam_choice - 1]
                    attempts = viewer.get_all_attempts(exam_id=selected_exam['id'])
                    print(f"\n🔍 Showing attempts for exam: {selected_exam['name']}")
                    display_attempts_table(attempts)
                else:
                    print("❌ Invalid exam selection!")
            except ValueError:
                print("❌ Please enter a valid number!")
        
        elif choice == '4':
            stats = viewer.get_attempt_statistics()
            display_statistics(stats)
        
        elif choice == '5':
            search_term = get_simple_input("Enter task search term (e.g., 'S1B2A3' or '3.1'): ").strip()
            if search_term:
                attempts = viewer.get_all_attempts()
                # Filter attempts by task number
                filtered_attempts = []
                for attempt in attempts:
                    task_info = f"S{attempt['semester']}B{attempt['sheet_number']}A{attempt['task_number']}"
                    if (search_term.lower() in task_info.lower() or 
                        search_term.lower() in attempt['task_number'].lower()):
                        filtered_attempts.append(attempt)
                
                print(f"\n🔍 Search results for '{search_term}':")
                display_attempts_table(filtered_attempts)
            else:
                print("❌ Please enter a search term!")
        
        elif choice == '6':
            print("👋 Goodbye!")
            break
        
        else:
            print("❌ Invalid choice! Please select 1-6.")

if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        print("\n\n👋 Goodbye!")
    except Exception as e:
        print(f"\n❌ Error: {e}")
        print("Please check your database and try again.")
