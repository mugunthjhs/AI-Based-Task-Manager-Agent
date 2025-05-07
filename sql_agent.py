from langchain_community.agent_toolkits import create_sql_agent
from langchain_community.agent_toolkits.sql.toolkit import SQLDatabaseToolkit
from langchain_community.utilities.sql_database import SQLDatabase
from langchain.llms import Ollama
from datetime import datetime

# Hardcoded user details
user_name = "Mugunth"
user_email = "smjharish2003@gmail.com"

def create_task_agent():
    # Get today's day and date for relative time resolution
    today_str = datetime.now().strftime("%A, %d %B %Y")  # Example: Tuesday, 07 May 2025

    # Connect to SQLite database
    db = SQLDatabase.from_uri("sqlite:///tasks.db")

    # Initialize Ollama with Qwen model
    llm = Ollama(model="qwen")

    # Prompt guiding the SQL agent
    prompt_prefix = f"""
    You are a task management assistant.

    The current user is:
    - Name: {user_name}
    - Email: {user_email}

    Using the user's email, you can filter and manage tasks in the database.
    All actions should be scoped to this user.

    Your responsibilities:
    1. Accept a natural language task-related query (e.g., "I have a meeting tomorrow at 2pm").
    2. Generate the corresponding SQL code using the tasks table.
    3. Execute the SQL query against the database.
    4. Use the output to form a clear, helpful response to the user.

    Database Table: tasks
    Columns:
    - id (INTEGER PRIMARY KEY AUTOINCREMENT)
    - user_name (TEXT)
    - user_email (TEXT)
    - task_name (TEXT)
    - status (TEXT, default 'pending')
    - category (TEXT)
    - created_at (TEXT, default current timestamp)
    - due_date (TEXT)

    Always:
    - Filter queries by user_email = '{user_email}'.
    - Provide friendly confirmations for add/update/delete actions.
    - Summarize task data in a readable format for view actions.
    - Resolve relative time expressions (e.g., 'tomorrow', 'next Monday') based on: {today_str}.
    """

    # Create the SQL agent
    agent = create_sql_agent(
        llm=llm,
        toolkit=SQLDatabaseToolkit(llm=llm, db=db),
        verbose=True,
        prefix=prompt_prefix
    )

    return agent

if __name__ == "__main__":
    print("✅ Task Manager SQL Agent is ready for:")
    print(f"👤 User: {user_name} ({user_email})")
    print("💬 Enter a task-related query or type 'exit' to quit.")

    agent = create_task_agent()

    while True:
        query = "I have a meeting tomorrow at 2pm"
        if query.strip().lower() in ["exit", "quit"]:
            print("👋 Goodbye!")
            break

        try:
            response = agent.run(query)
            print(f"\n🤖 Agent:\n{response}")
        except Exception as e:
            print(f"\n❌ Error: {e}")
