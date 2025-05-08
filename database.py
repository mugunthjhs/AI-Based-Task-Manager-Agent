import sqlite3
from langchain_community.utilities.sql_database import SQLDatabase

DB_FILENAME = "tasks.db"
DB_PATH_URI = f"sqlite:///{DB_FILENAME}"

def create_db_and_table():
    conn = sqlite3.connect(DB_FILENAME)
    cursor = conn.cursor()
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS tasks (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        user_name TEXT,
        user_email TEXT,
        task_name TEXT NOT NULL,
        status TEXT DEFAULT 'pending',
        category TEXT,
        created_at TEXT DEFAULT (strftime('%Y-%m-%d %H:%M:%S', 'now', 'localtime')),
        due_date TEXT,
        due_time TEXT
    )
    """)
    try:
        cursor.execute("""
        CREATE UNIQUE INDEX IF NOT EXISTS idx_unq_user_task
        ON tasks (user_email, task_name, due_date, COALESCE(due_time, ''));
        """)
    except sqlite3.OperationalError as e:
        print(f"Warning: Could not create unique index idx_unq_user_task, it might exist or conflict: {e}")
    conn.commit()
    conn.close()

def get_db_info():
    db = SQLDatabase.from_uri(DB_PATH_URI, include_tables=['tasks'])
    return db.get_table_info()

def get_task_by_id(task_id: int, user_email: str):
    query = "SELECT id, task_name, status, category, due_date, due_time, created_at FROM tasks WHERE id = ? AND user_email = ?"
    conn = sqlite3.connect(DB_FILENAME)
    cursor = conn.cursor()
    try:
        cursor.execute(query, (task_id, user_email))
        data = cursor.fetchone()
        if data:
            columns = [description[0] for description in cursor.description]
            return dict(zip(columns, data))
        return None
    except sqlite3.Error as e:
        print(f"Error fetching task by ID {task_id}: {e}")
        return None
    finally:
        conn.close()

def execute_select_query(query: str, params: tuple = None):
    conn = sqlite3.connect(DB_FILENAME)
    cursor = conn.cursor()
    try:
        cursor.execute(query, params or ())
        data = cursor.fetchall()
        columns = [description[0] for description in cursor.description] if cursor.description else []
        return data, columns
    except sqlite3.Error as e:
        print(f"Error executing SELECT query: {query}\n{e}")
        raise
    finally:
        conn.close()

def execute_dml_query(query: str, params: tuple = None):
    conn = sqlite3.connect(DB_FILENAME)
    cursor = conn.cursor()
    is_insert = query.strip().upper().startswith("INSERT")
    try:
        cursor.execute(query, params or ())
        conn.commit()
        if is_insert:
            return cursor.lastrowid
        return cursor.rowcount
    
    except sqlite3.IntegrityError as e: 
        error_code = getattr(e, 'sqlite_errorcode', None) 
        if not error_code and hasattr(e, 'args') and len(e.args) > 0: 
            if "UNIQUE constraint failed" in str(e.args[0]).upper(): 
                 error_code = 2067 
        if error_code == 2067 or error_code == 1555 or \
           (isinstance(e, sqlite3.IntegrityError) and "UNIQUE constraint failed" in str(e).upper()):
            raise ValueError(f"Task likely already exists with the same name, due date, and time. (Details: {e})")
        else:
            print(f"Unhandled IntegrityError executing DML query: {query}\nCode: {error_code}, Error: {e}")
            raise 

    except sqlite3.Error as e:
        print(f"General SQLite error executing DML query: {query}\n{e}")
        raise
    finally:
        conn.close()