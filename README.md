# AI-Based Task Manager Agent 🤖📝

**Live Application:** [https://ai-based-task-manager-agent.streamlit.app/](https://ai-based-task-manager-agent.streamlit.app/)

---

## Overview

The AI-Based Task Manager is an intelligent agent designed to help you manage your tasks seamlessly using natural language. Instead of navigating complex menus or forms, simply tell the agent what you need to do, and it will handle the organization, categorization, and storage of your tasks in a dedicated database.

This application leverages the power of Large Language Models (LLMs) through Google's Generative AI (Gemini Pro) to understand your requests, convert them into actionable database operations, and provide clear, human-readable feedback. The user interface is built with Streamlit, offering a clean and interactive experience.

---

## Key Features

*   **Natural Language Task Input:** Add, view, update, and delete tasks by typing commands in plain English (e.g., "Add 'Buy groceries due tomorrow at 5pm' category Personal", "Show me pending tasks", "Mark 'Call John' as completed").
*   **Intelligent Task Categorization:** The AI attempts to automatically categorize your tasks (e.g., Work, Personal, Meeting) for better organization.
*   **Contextual Follow-up:** The agent remembers the last task you interacted with, allowing for intuitive follow-up commands like "Mark it as done" or "Cancel that meeting."
*   **Due Date & Time Parsing:** Understands relative dates ("tomorrow", "next Friday") and specific times ("at 3pm", "by 17:00").
*   **User-Specific Task Management:** Tasks are tied to your email, ensuring privacy and personal organization.
*   **SQLite Database Backend:** Tasks are stored persistently (within the limits of the deployment environment) in a local SQLite database.
*   **Streamlit Interface:** A user-friendly web interface for easy interaction.
*   **Secure Login:** Email validation ensures a basic level of user identification (requires `.com` emails for this demo).

---

## How It Works (Technical Summary)

1.  **User Input:** You provide a task-related command in natural language via the Streamlit interface.
2.  **LLM for SQL Generation:** The input, along with user context (name, email, previous task) and database schema information, is sent to a Google Generative AI model (Gemini Pro).
3.  **SQL Prompt Engineering:** A carefully crafted prompt guides the LLM to:
    *   Translate the natural language request into an SQLite query.
    *   Infer categories, parse dates/times, and handle contextual references.
    *   Adhere to specific SQL rules for data integrity and security (e.g., always filtering by `user_email`).
4.  **Database Interaction:** The generated SQLite query is executed against a local `tasks.db` file.
    *   **Schema:** The `tasks` table includes fields like `id`, `user_name`, `user_email`, `task_name`, `status`, `category`, `created_at`, `due_date`, and `due_time`.
    *   **Uniqueness:** A unique index helps prevent duplicate task entries for the same user, task name, due date, and time.
5.  **Result & Summarization:**
    *   For data retrieval (SELECT), results are displayed in a structured format (Pandas DataFrame).
    *   For data modification (INSERT, UPDATE, DELETE), a success message is shown.
    *   The LLM is then used again to provide a friendly, human-readable summary of the action taken and its outcome.
6.  **Contextual Memory:** The application maintains a short-term memory of the last interacted task to enable more natural follow-up commands.

---

## Project Structure

The application is organized into the following key Python files:

*   `app.py`: The main Streamlit application. Handles user interface, login, session management, and orchestrates calls to the LLM handler and database modules.
*   `llm_handler.py`: Manages all interactions with the Google Generative AI model. Contains prompt templates for SQL generation and result summarization, and functions to invoke the LLM.
*   `database.py`: Handles all direct SQLite database operations. Includes functions for creating the database and table, executing DML (Data Manipulation Language) and SELECT queries, and fetching specific task details.
*   `Dockerfile`: Defines the container environment for deploying the application on platforms like Hugging Face Spaces.
*   `requirements.txt`: Lists all Python package dependencies.
*   `.env` (local only, not in repo): Stores the `GOOGLE_API_KEY` for local development. For deployment, this key is managed as a secret in the hosting environment.
*   `tasks.db` (created at runtime): The SQLite database file where task data is stored. *Note: On the current free-tier deployment, this database is ephemeral and data will be lost on application restarts.*

---

## Limitations (Current Free Tier Deployment)

*   **Ephemeral Data Storage:** The live application linked above is deployed on a free tier of Hugging Face Spaces. Due to the nature of free-tier ephemeral filesystems, **all task data entered will be lost when the application restarts or is redeployed.** This version is primarily for demonstration purposes. True data persistence would require a paid persistent storage solution or an external database.
*   **LLM Imperfections:** While powerful, LLMs can sometimes misinterpret complex or ambiguous requests, potentially leading to incorrect SQL generation or unexpected behavior. Prompt engineering aims to minimize this, but it's an ongoing area of refinement.
*   **Context Window:** The "memory" for follow-up commands is limited to the most recently interacted task.

---

This AI Task Manager showcases the potential of combining LLMs with traditional software components to create more intuitive and powerful user experiences.
