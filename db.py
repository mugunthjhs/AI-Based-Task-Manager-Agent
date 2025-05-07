import sqlite3
from datetime import datetime

def init_db():
    conn = sqlite3.connect("tasks.db")
    c = conn.cursor()
    c.execute("""
    CREATE TABLE IF NOT EXISTS tasks (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        user_name TEXT,
        user_email TEXT,
        task_name TEXT,
        status TEXT,
        category TEXT,
        created_at TEXT,
        due_date TEXT
    )""")
    conn.commit()
    conn.close()

def insert_sample_tasks():
    conn = sqlite3.connect("tasks.db")
    c = conn.cursor()

    sample_tasks = [
        ("Mugunth", "smjharish2003@gmail.com", "Prepare Quarterly Report", "Pending", "Work", "2025-05-07", "2025-05-10"),
        ("Mugunth", "smjharish2003@gmail.com", "Buy Groceries for the Week", "Completed", "Personal", "2025-05-07", "2025-05-08"),
        ("Mugunth", "smjharish2003@gmail.com", "Complete Python Course Assignment", "Pending", "Study", "2025-05-07", "2025-05-15"),
        ("Mugunth", "smjharish2003@gmail.com", "Read Chapter 5 of 'AI for Beginners'", "In Progress", "Study", "2025-05-07", "2025-05-12"),
        ("Mugunth", "smjharish2003@gmail.com", "Call Mom", "Pending", "Personal", "2025-05-07", "2025-05-14"),
        ("Mugunth", "smjharish2003@gmail.com", "Finish Project Proposal Draft", "Completed", "Work", "2025-05-07", "2025-05-09"),
        ("Mugunth", "smjharish2003@gmail.com", "Plan Weekend Trip to Beach", "In Progress", "Personal", "2025-05-07", "2025-05-20"),
        ("Mugunth", "smjharish2003@gmail.com", "Review Meeting Notes and Send Feedback", "Pending", "Work", "2025-05-07", "2025-05-25"),
        ("Mugunth", "smjharish2003@gmail.com", "Organize Digital Files on Laptop", "Completed", "Personal", "2025-05-07", "2025-05-11"),
        ("Mugunth", "smjharish2003@gmail.com", "Update Resume for New Job Opportunities", "In Progress", "Work", "2025-05-07", "2025-05-30")
    ]

    for task in sample_tasks:
        c.execute("""
        INSERT INTO tasks (user_name, user_email, task_name, status, category, created_at, due_date)
        VALUES (?, ?, ?, ?, ?, ?, ?)
        """, task)

    conn.commit()
    conn.close()

if __name__ == "__main__":
    init_db()
    insert_sample_tasks()
    print("Database initialized and sample tasks inserted.")