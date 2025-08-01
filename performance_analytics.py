#!/usr/bin/env python3
"""
Performance Analytics Script for Physics Learning System

This script provides comprehensive analytics including:
- Time per point over time plots
- Task completion statistics
- Performance trends
- Exam-specific analytics
"""

import matplotlib.pyplot as plt
import matplotlib.dates as mdates
from datetime import datetime, timedelta
import numpy as np
from typing import List, Dict, Optional, Tuple
from database.models import DatabaseManager
from exam_manager import ExamManager
from utils.keyboard import get_simple_input
import sqlite3

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

class PerformanceAnalyzer:
    def __init__(self, db_manager: DatabaseManager):
        self.db_manager = db_manager
        self.exam_id = None
        self.exam_name = "All Exams"
    
    def set_exam(self, exam_id: int, exam_name: str):
        """Set the exam to analyze"""
        self.exam_id = exam_id
        self.exam_name = exam_name
    
    def get_time_per_point_data(self) -> List[Dict]:
        """Get time per point data over time"""
        conn = self.db_manager.get_connection()
        cursor = conn.cursor()
        
        query = '''
            SELECT 
                sa.attempt_date,
                sa.total_time_seconds,
                t.total_points,
                t.task_number,
                w.semester,
                w.sheet_number,
                sa.created_at,
                CAST(sa.total_time_seconds AS FLOAT) / t.total_points as time_per_point
            FROM solution_attempts sa
            JOIN tasks t ON sa.task_id = t.id
            JOIN worksheets w ON t.worksheet_id = w.id
            WHERE sa.status = 'completed' 
            AND sa.total_time_seconds IS NOT NULL 
            AND t.total_points > 0
        '''
        
        params = []
        if self.exam_id:
            query += ' AND w.exam_id = ?'
            params.append(self.exam_id)
        
        query += ' ORDER BY sa.created_at'
        
        cursor.execute(query, params)
        results = cursor.fetchall()
        conn.close()
        
        data = []
        for row in results:
            data.append({
                'attempt_date': row[0],
                'total_time_seconds': row[1],
                'total_points': row[2],
                'task_number': row[3],
                'semester': row[4],
                'sheet_number': row[5],
                'created_at': row[6],
                'time_per_point': row[7]
            })
        
        return data
    
    def get_completion_statistics(self) -> Dict:
        """Get comprehensive completion statistics"""
        conn = self.db_manager.get_connection()
        cursor = conn.cursor()
        
        # Base query conditions
        exam_condition = ""
        params = []
        if self.exam_id:
            exam_condition = "AND w.exam_id = ?"
            params = [self.exam_id]
        
        # Total tasks and points
        cursor.execute(f'''
            SELECT 
                COUNT(DISTINCT t.id) as total_tasks,
                SUM(t.total_points) as total_points
            FROM tasks t
            JOIN worksheets w ON t.worksheet_id = w.id
            WHERE 1=1 {exam_condition}
        ''', params)
        total_stats = cursor.fetchone()
        total_tasks = total_stats[0] or 0
        total_points = total_stats[1] or 0
        
        # Tasks done at least once
        cursor.execute(f'''
            SELECT COUNT(DISTINCT t.id) as tasks_done_once
            FROM tasks t
            JOIN worksheets w ON t.worksheet_id = w.id
            WHERE t.times_done > 0 {exam_condition}
        ''', params)
        tasks_done_once = cursor.fetchone()[0] or 0
        
        # Points from tasks done at least once
        cursor.execute(f'''
            SELECT SUM(t.total_points) as points_done_once
            FROM tasks t
            JOIN worksheets w ON t.worksheet_id = w.id
            WHERE t.times_done > 0 {exam_condition}
        ''', params)
        points_done_once = cursor.fetchone()[0] or 0
        
        # Completion attempts statistics
        cursor.execute(f'''
            SELECT 
                COUNT(*) as total_attempts,
                COUNT(CASE WHEN sa.status = 'completed' THEN 1 END) as completed_attempts,
                COUNT(CASE WHEN sa.status = 'cancelled' THEN 1 END) as cancelled_attempts,
                SUM(CASE WHEN sa.status = 'completed' THEN sa.total_time_seconds END) as total_time_spent
            FROM solution_attempts sa
            JOIN tasks t ON sa.task_id = t.id
            JOIN worksheets w ON t.worksheet_id = w.id
            WHERE 1=1 {exam_condition}
        ''', params)
        attempt_stats = cursor.fetchone()
        
        # Average times by point range
        cursor.execute(f'''
            SELECT 
                CASE 
                    WHEN t.total_points <= 5 THEN '1-5 points'
                    WHEN t.total_points <= 10 THEN '6-10 points'
                    WHEN t.total_points <= 15 THEN '11-15 points'
                    ELSE '16+ points'
                END as point_range,
                COUNT(*) as attempts,
                AVG(sa.total_time_seconds) as avg_time,
                AVG(CAST(sa.total_time_seconds AS FLOAT) / t.total_points) as avg_time_per_point
            FROM solution_attempts sa
            JOIN tasks t ON sa.task_id = t.id
            JOIN worksheets w ON t.worksheet_id = w.id
            WHERE sa.status = 'completed' 
            AND sa.total_time_seconds IS NOT NULL 
            AND t.total_points > 0 {exam_condition}
            GROUP BY point_range
            ORDER BY MIN(t.total_points)
        ''', params)
        point_range_stats = cursor.fetchall()
        
        # Most and least efficient tasks (time per point)
        cursor.execute(f'''
            SELECT 
                PRINTF('S%dB%dA%s', w.semester, w.sheet_number, t.task_number) as task_info,
                t.total_points,
                COUNT(*) as attempts,
                AVG(CAST(sa.total_time_seconds AS FLOAT) / t.total_points) as avg_time_per_point,
                MIN(CAST(sa.total_time_seconds AS FLOAT) / t.total_points) as best_time_per_point,
                MAX(CAST(sa.total_time_seconds AS FLOAT) / t.total_points) as worst_time_per_point
            FROM solution_attempts sa
            JOIN tasks t ON sa.task_id = t.id
            JOIN worksheets w ON t.worksheet_id = w.id
            WHERE sa.status = 'completed' 
            AND sa.total_time_seconds IS NOT NULL 
            AND t.total_points > 0 {exam_condition}
            GROUP BY t.id
            HAVING COUNT(*) >= 1
            ORDER BY avg_time_per_point
        ''', params)
        efficiency_stats = cursor.fetchall()
        
        # Weekly progress (last 8 weeks)
        cursor.execute(f'''
            SELECT 
                DATE(sa.created_at, 'weekday 0', '-6 days') as week_start,
                COUNT(CASE WHEN sa.status = 'completed' THEN 1 END) as completed_tasks,
                SUM(CASE WHEN sa.status = 'completed' THEN sa.total_time_seconds END) as total_time,
                COUNT(DISTINCT t.id) as unique_tasks
            FROM solution_attempts sa
            JOIN tasks t ON sa.task_id = t.id
            JOIN worksheets w ON t.worksheet_id = w.id
            WHERE sa.created_at >= DATE('now', '-8 weeks') {exam_condition}
            GROUP BY week_start
            ORDER BY week_start
        ''', params)
        weekly_stats = cursor.fetchall()
        
        conn.close()
        
        return {
            'total_tasks': total_tasks,
            'total_points': total_points,
            'tasks_done_once': tasks_done_once,
            'points_done_once': points_done_once,
            'task_completion_percentage': (tasks_done_once / total_tasks * 100) if total_tasks > 0 else 0,
            'point_completion_percentage': (points_done_once / total_points * 100) if total_points > 0 else 0,
            'total_attempts': attempt_stats[0] or 0,
            'completed_attempts': attempt_stats[1] or 0,
            'cancelled_attempts': attempt_stats[2] or 0,
            'total_time_spent': attempt_stats[3] or 0,
            'success_rate': (attempt_stats[1] / attempt_stats[0] * 100) if attempt_stats[0] > 0 else 0,
            'point_range_stats': point_range_stats,
            'efficiency_stats': efficiency_stats,
            'weekly_stats': weekly_stats
        }
    
    def plot_time_per_point_over_time(self, data: List[Dict]):
        """Create a plot showing time per point over time"""
        if not data:
            print("❌ No data available for plotting")
            return
        
        # Convert dates and prepare data
        dates = []
        times_per_point = []
        point_sizes = []
        
        for entry in data:
            try:
                # Parse the created_at timestamp
                date_obj = datetime.strptime(entry['created_at'], '%Y-%m-%d %H:%M:%S')
                dates.append(date_obj)
                times_per_point.append(entry['time_per_point'])
                # Size points based on total points (for visual emphasis)
                point_sizes.append(entry['total_points'] * 10)
            except (ValueError, TypeError):
                continue
        
        if not dates:
            print("❌ No valid date data for plotting")
            return
        
        # Create the plot
        plt.figure(figsize=(14, 8))
        
        # Main scatter plot
        scatter = plt.scatter(dates, times_per_point, s=point_sizes, alpha=0.6, c=times_per_point, 
                            cmap='RdYlBu_r', edgecolors='black', linewidth=0.5)
        
        # Add trend line
        if len(dates) > 1:
            # Convert dates to numbers for trend calculation
            date_nums = [mdates.date2num(date) for date in dates]
            z = np.polyfit(date_nums, times_per_point, 1)
            p = np.poly1d(z)
            plt.plot(dates, p(date_nums), "r--", alpha=0.8, linewidth=2, label=f'Trend (slope: {z[0]:.2f} sec/point per day)')
        
        # Formatting
        plt.title(f'Time per Point Over Time - {self.exam_name}', fontsize=16, fontweight='bold')
        plt.xlabel('Date', fontsize=12)
        plt.ylabel('Time per Point (seconds)', fontsize=12)
        plt.grid(True, alpha=0.3)
        
        # Format x-axis
        plt.gca().xaxis.set_major_formatter(mdates.DateFormatter('%Y-%m-%d'))
        plt.gca().xaxis.set_major_locator(mdates.WeekdayLocator(interval=1))
        plt.xticks(rotation=45)
        
        # Add colorbar
        cbar = plt.colorbar(scatter)
        cbar.set_label('Time per Point (seconds)', rotation=270, labelpad=20)
        
        # Add legend
        plt.legend()
        
        # Add statistics text
        avg_time_per_point = np.mean(times_per_point)
        median_time_per_point = np.median(times_per_point)
        std_time_per_point = np.std(times_per_point)
        
        stats_text = f'Avg: {avg_time_per_point:.1f}s/pt\nMedian: {median_time_per_point:.1f}s/pt\nStd: {std_time_per_point:.1f}s/pt'
        plt.text(0.02, 0.98, stats_text, transform=plt.gca().transAxes, 
                verticalalignment='top', bbox=dict(boxstyle='round', facecolor='wheat', alpha=0.8))
        
        plt.tight_layout()
        plt.show()
    
    def plot_weekly_progress(self, weekly_stats: List[Tuple]):
        """Plot weekly progress over time"""
        if not weekly_stats:
            print("❌ No weekly data available for plotting")
            return
        
        weeks = []
        completed_tasks = []
        total_times = []
        unique_tasks = []
        
        for week_data in weekly_stats:
            try:
                week_start = datetime.strptime(week_data[0], '%Y-%m-%d')
                weeks.append(week_start)
                completed_tasks.append(week_data[1] or 0)
                total_times.append((week_data[2] or 0) / 3600)  # Convert to hours
                unique_tasks.append(week_data[3] or 0)
            except (ValueError, TypeError):
                continue
        
        if not weeks:
            print("❌ No valid weekly data for plotting")
            return
        
        # Create subplots
        fig, (ax1, ax2, ax3) = plt.subplots(3, 1, figsize=(12, 10))
        
        # Plot 1: Completed tasks per week
        ax1.bar(weeks, completed_tasks, alpha=0.7, color='skyblue', edgecolor='navy')
        ax1.set_title(f'Weekly Completed Tasks - {self.exam_name}', fontweight='bold')
        ax1.set_ylabel('Completed Tasks')
        ax1.grid(True, alpha=0.3)
        
        # Plot 2: Time spent per week
        ax2.bar(weeks, total_times, alpha=0.7, color='lightgreen', edgecolor='darkgreen')
        ax2.set_title('Weekly Time Spent (Hours)', fontweight='bold')
        ax2.set_ylabel('Hours')
        ax2.grid(True, alpha=0.3)
        
        # Plot 3: Unique tasks per week
        ax3.bar(weeks, unique_tasks, alpha=0.7, color='salmon', edgecolor='darkred')
        ax3.set_title('Weekly Unique Tasks Attempted', fontweight='bold')
        ax3.set_ylabel('Unique Tasks')
        ax3.set_xlabel('Week Starting')
        ax3.grid(True, alpha=0.3)
        
        # Format x-axis for all plots
        for ax in [ax1, ax2, ax3]:
            ax.xaxis.set_major_formatter(mdates.DateFormatter('%m/%d'))
            ax.xaxis.set_major_locator(mdates.WeekdayLocator(interval=1))
            plt.setp(ax.xaxis.get_majorticklabels(), rotation=45)
        
        plt.tight_layout()
        plt.show()
    
    def print_detailed_statistics(self, stats: Dict):
        """Print comprehensive statistics"""
        print(f"\n📊 Detailed Statistics for {self.exam_name}")
        print("=" * 60)
        
        # Overall completion stats
        print(f"\n🎯 Overall Progress:")
        print(f"   Total Tasks Available: {stats['total_tasks']}")
        print(f"   Total Points Available: {stats['total_points']}")
        print(f"   Tasks Done At Least Once: {stats['tasks_done_once']} ({stats['task_completion_percentage']:.1f}%)")
        print(f"   Points Done At Least Once: {stats['points_done_once']} ({stats['point_completion_percentage']:.1f}%)")
        
        # Attempt statistics
        print(f"\n📈 Attempt Statistics:")
        print(f"   Total Attempts: {stats['total_attempts']}")
        print(f"   Completed Attempts: {stats['completed_attempts']}")
        print(f"   Cancelled Attempts: {stats['cancelled_attempts']}")
        print(f"   Success Rate: {stats['success_rate']:.1f}%")
        print(f"   Total Time Spent: {format_time(stats['total_time_spent'])}")
        
        # Average time by point range
        if stats['point_range_stats']:
            print(f"\n⏱️  Performance by Point Range:")
            for point_range, attempts, avg_time, avg_time_per_point in stats['point_range_stats']:
                print(f"   {point_range:<12}: {attempts:>3} attempts, "
                      f"avg {format_time(int(avg_time) if avg_time else 0)}, "
                      f"{avg_time_per_point:.1f}s/point")
        
        # Most and least efficient tasks
        if stats['efficiency_stats']:
            print(f"\n🏆 Most Efficient Tasks (lowest time/point):")
            for i, (task_info, points, attempts, avg_tpp, best_tpp, worst_tpp) in enumerate(stats['efficiency_stats'][:5], 1):
                print(f"   {i}. {task_info} ({points}pts): {avg_tpp:.1f}s/pt avg ({attempts} attempts)")
            
            if len(stats['efficiency_stats']) > 5:
                print(f"\n🐌 Least Efficient Tasks (highest time/point):")
                for i, (task_info, points, attempts, avg_tpp, best_tpp, worst_tpp) in enumerate(stats['efficiency_stats'][-5:], 1):
                    print(f"   {i}. {task_info} ({points}pts): {avg_tpp:.1f}s/pt avg ({attempts} attempts)")
        
        # Weekly summary
        if stats['weekly_stats']:
            print(f"\n📅 Recent Weekly Activity:")
            total_weekly_tasks = sum(week[1] or 0 for week in stats['weekly_stats'])
            total_weekly_time = sum(week[2] or 0 for week in stats['weekly_stats'])
            print(f"   Last {len(stats['weekly_stats'])} weeks: {total_weekly_tasks} tasks completed")
            print(f"   Total time: {format_time(total_weekly_time)}")
            if len(stats['weekly_stats']) > 0:
                avg_weekly_tasks = total_weekly_tasks / len(stats['weekly_stats'])
                print(f"   Average per week: {avg_weekly_tasks:.1f} tasks")

def select_exam_for_analysis(db_manager: DatabaseManager) -> Tuple[Optional[int], str]:
    """Allow user to select an exam for analysis"""
    exam_manager = ExamManager(db_manager)
    exams = exam_manager.list_exams()
    
    if not exams:
        print("❌ No exams found!")
        return None, "No Exams"
    
    print("\n📋 Available Exams for Analysis:")
    print("0. All Exams (combined analysis)")
    for i, exam in enumerate(exams, 1):
        print(f"{i}. {exam['name']} ({exam['task_count']} tasks)")
    
    while True:
        try:
            choice = int(get_simple_input("\nSelect exam (number): ").strip())
            if choice == 0:
                return None, "All Exams"
            elif 1 <= choice <= len(exams):
                selected_exam = exams[choice - 1]
                return selected_exam['id'], selected_exam['name']
            else:
                print(f"❌ Please enter a number between 0 and {len(exams)}")
        except ValueError:
            print("❌ Please enter a valid number")

def main():
    """Main function for performance analytics"""
    print("=== 📊 Performance Analytics ===")
    print("Comprehensive analysis of your learning progress")
    
    # Initialize database
    db_manager = DatabaseManager()
    db_manager.init_database()
    
    # Select exam for analysis
    exam_id, exam_name = select_exam_for_analysis(db_manager)
    
    analyzer = PerformanceAnalyzer(db_manager)
    if exam_id:
        analyzer.set_exam(exam_id, exam_name)
    
    print(f"\n✅ Analyzing data for: {exam_name}")
    
    while True:
        print("\n" + "="*50)
        print(f"Current Analysis: {exam_name}")
        print("1. Plot time per point over time")
        print("2. Show detailed statistics")
        print("3. Plot weekly progress")
        print("4. Show all analytics (plots + stats)")
        print("5. Switch exam")
        print("6. Exit")
        
        choice = get_simple_input("\nSelect option: ").strip()
        
        if choice == '1':
            print("📈 Generating time per point plot...")
            data = analyzer.get_time_per_point_data()
            analyzer.plot_time_per_point_over_time(data)
        
        elif choice == '2':
            print("📊 Calculating detailed statistics...")
            stats = analyzer.get_completion_statistics()
            analyzer.print_detailed_statistics(stats)
        
        elif choice == '3':
            print("📅 Generating weekly progress plot...")
            stats = analyzer.get_completion_statistics()
            analyzer.plot_weekly_progress(stats['weekly_stats'])
        
        elif choice == '4':
            print("🔍 Generating complete analytics...")
            data = analyzer.get_time_per_point_data()
            stats = analyzer.get_completion_statistics()
            
            # Show statistics first
            analyzer.print_detailed_statistics(stats)
            
            # Then show plots
            print("\n📈 Showing time per point plot...")
            analyzer.plot_time_per_point_over_time(data)
            
            print("\n📅 Showing weekly progress plot...")
            analyzer.plot_weekly_progress(stats['weekly_stats'])
        
        elif choice == '5':
            exam_id, exam_name = select_exam_for_analysis(db_manager)
            analyzer = PerformanceAnalyzer(db_manager)
            if exam_id:
                analyzer.set_exam(exam_id, exam_name)
            print(f"✅ Switched to: {exam_name}")
        
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
        import traceback
        traceback.print_exc()
