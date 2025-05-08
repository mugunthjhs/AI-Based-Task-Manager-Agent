import os
from langchain_google_genai.llms import GoogleGenerativeAI
from langchain_core.prompts import PromptTemplate
from dotenv import load_dotenv
from datetime import datetime

load_dotenv()
GOOGLE_API_KEY = os.getenv("GOOGLE_API_KEY")

SQL_GENERATION_PROMPT_TEMPLATE = """
You are an AI assistant that translates user requests into SQLite queries for a task management system.
Your goal is to generate a SINGLE, EXECUTABLE SQLite query.

Current User:
- Name: {user_name}
- Email: {user_email}

Today's Date: {today_date}. Resolve relative dates like 'today', 'tomorrow', 'next week'.
Due dates should be in 'YYYY-MM-DD' format.
'due_time' should be in 'HH:MM' (24-hour) format if specified (e.g., "2pm" becomes "14:00", "9 AM" becomes "09:00"). If no time is given for a due date, `due_time` should be NULL or omitted from INSERT if the column allows NULLs.
'created_at' is automatically handled by the database.
'status' defaults to 'pending' if not specified for new tasks.

Database Table Schema (tasks table):
{table_info}
/*
CREATE TABLE tasks (
        id INTEGER PRIMARY KEY AUTOINCREMENT,       -- Unique ID for the task
        user_name TEXT,                             -- Name of the user
        user_email TEXT,                            -- Email of the user (for filtering)
        task_name TEXT NOT NULL,                    -- Description of the task
        status TEXT DEFAULT 'pending',              -- e.g., 'pending', 'completed', 'cancelled'
        category TEXT,                              -- e.g., 'Work', 'Personal', 'School'
        created_at TEXT DEFAULT (strftime('%Y-%m-%d %H:%M:%S', 'now', 'localtime')), -- Timestamp of creation
        due_date TEXT,                              -- Due date in YYYY-MM-DD format
        due_time TEXT                               -- Due time in HH:MM format (optional, can be NULL)
)
*/

SQL Generation Rules:
1.  **Targeting User Data**:
    - For `SELECT`, `UPDATE`, `DELETE` queries, ALWAYS include `WHERE user_email = '{user_email}'`.
    - For `INSERT` queries, ALWAYS include `user_name = '{user_name}'` and `user_email = '{user_email}'` in the `VALUES`.
2.  **Specificity and Column Selection**:
    - **Task Name Normalization (for INSERTs):** When creating a new task, try to use a concise and normalized version of the task description provided by the user as the 'task_name'. For example, if the user says "I have a meeting tomorroww at 2pm about project alpha", the task_name could be "Meeting about project alpha" or "Project alpha meeting". Avoid including conversational fluff like "I have a" directly in the task_name unless it's essential to the task's identity. Ensure correct spelling for common words like "tomorrow".
    - Do NOT use `SELECT *`. Explicitly list columns: `id, task_name, status, category, due_date, due_time, created_at`.
    - For `UPDATE` or `DELETE`, ensure the `WHERE` clause is specific. Use `task_name` (possibly with `LIKE '%task_name_fragment%'`), `id` (if known from context), `due_date`, and/or `due_time`.
3.  **Task Categorization (for INSERTs)**:
    - ALWAYS attempt to infer a 'category' (e.g., 'Work', 'Personal', 'School', 'Meeting'). If not inferable, use 'General'.
4.  **Date and Time Handling**:
    - Use SQLite date functions like `DATE('now')`, `DATE('now', '+X days')`.
    - Ensure `due_date` is 'YYYY-MM-DD'. Use `>=` for "greater than or equal to".
    - If time is mentioned (e.g., "at 2pm", "by 17:00"), extract it and store in `due_time` as 'HH:MM' (24-hour format). If no time, `due_time` is NULL.
5.  **Default Ordering**: For `SELECT` queries listing multiple tasks, order by `due_date ASC NULLS LAST`, then `due_time ASC NULLS LAST`, then `created_at DESC`.
6.  **Contextual Follow-up Actions (IMPORTANT)**:
    - The `Previous relevant task context` might contain `id`, `task_name`, `due_date`, `due_time` of a recently discussed task.
    - If the user's query seems to refer to this contextual task (e.g., "mark *it* as done", "attended *the school meeting*", "cancel *that task*"), use the details from the context, especially the `id` if available, to form a precise `WHERE` clause for `UPDATE` or `DELETE`.
    - Example: User adds "School meeting Friday 2pm". Context: `id: 123, name: School meeting...`. Next query: "I attended it". SQL should be `UPDATE tasks SET status = 'completed' WHERE id = 123 AND user_email = '{user_email}'`.
    - If the current query provides overriding details (e.g., "cancel the meeting on *next Monday*"), prioritize these new details. However, if it's "cancel *the* meeting" and context has a meeting, use context.
    - If multiple tasks match a vague description without strong context, target the most recently created one or the one with the nearest due date that matches.
7.  **Status Updates**:
    - "Attended", "finished", "done" usually mean `status = 'completed'`.
    - "Cancel" can mean `status = 'cancelled'` or `DELETE`. Prefer `DELETE` if the user says "cancel the meeting" and implies it should be removed. If they say "the meeting is cancelled", `UPDATE status = 'cancelled'` might be more appropriate. Use your best judgment based on phrasing. For "cancel the meeting on next monday", this usually implies DELETE.
8.  **Output Format**: Generate ONLY the SQLite query. No explanations, comments, or markdown like ```sql.

User Query: {input}
Previous relevant task context (if any): {previous_task_context}

SQLiteQuery:
"""

RESULT_SUMMARY_PROMPT_TEMPLATE = """
Based on the user's original request, the SQL query executed, and the result from the database, provide a concise, friendly, and human-readable summary.
Be direct and confirm the action taken or the information found. If a task was modified or added, mention its name.

Original User Query: {user_query}
SQL Query Executed: {sql_query}
SQL Query Result/Effect: {sql_result_str}

Friendly Summary:
"""


def get_llm():
    if not GOOGLE_API_KEY:
        raise ValueError("GOOGLE_API_KEY not found in environment variables.")
    return GoogleGenerativeAI(
        model="gemini-1.5-pro-latest",
        google_api_key=GOOGLE_API_KEY,
        temperature=0.05,   
    )

def get_sql_generation_prompt():
    return PromptTemplate(
        input_variables=["input", "table_info", "user_name", "user_email", "today_date", "previous_task_context"],
        template=SQL_GENERATION_PROMPT_TEMPLATE
    )

def get_result_summary_prompt():
    return PromptTemplate(
        input_variables=["user_query", "sql_query", "sql_result_str"],
        template=RESULT_SUMMARY_PROMPT_TEMPLATE
    )

def generate_sql_query(llm, user_query: str, table_info: str, user_name: str, user_email: str, previous_task_context: str) -> str:
    prompt = get_sql_generation_prompt()
    today_str = datetime.now().strftime("%A, %d %B %Y (%Y-%m-%d)")

    formatted_prompt = prompt.format(
        input=user_query,
        table_info=table_info,
        user_name=user_name,
        user_email=user_email,
        today_date=today_str,
        previous_task_context=previous_task_context
    )
    response = llm.invoke(formatted_prompt)
    generated_sql = response.strip()

    if generated_sql.startswith("```sql"):
        generated_sql = generated_sql[len("```sql"):].strip()
    if generated_sql.endswith("```"):
        generated_sql = generated_sql[:-len("```")].strip()

    prefixes_to_strip = [
        "SQLITEQUERY:", 
        "SQLQUERY:",
        "SQLITE:",
        "SQL:",
        "ITE"
    ]
    
    temp_sql_upper = generated_sql.upper()
    for prefix_candidate in prefixes_to_strip:
        if temp_sql_upper.startswith(prefix_candidate):
            generated_sql = generated_sql[len(prefix_candidate):].strip()
            temp_sql_upper = generated_sql.upper() 
    generated_sql = generated_sql.replace("≥", ">=").replace("≤", "<=")

    # print(f"[DEBUG] LLM_HANDLER Cleaned SQL: '{generated_sql}'")
    return generated_sql

def summarize_query_result(llm, user_query: str, sql_query: str, sql_result_str: str) -> str:
    prompt = get_result_summary_prompt()
    formatted_prompt = prompt.format(
        user_query=user_query,
        sql_query=sql_query,
        sql_result_str=sql_result_str
    )
    summary = llm.invoke(formatted_prompt)
    return summary.strip()