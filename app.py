import streamlit as st
import pandas as pd
from datetime import datetime
import database as db
import llm_handler
import sqlite3 # For specific error handling

# --- Page Configuration ---
st.set_page_config(page_title="AI Task Manager", layout="centered", initial_sidebar_state="collapsed")

# --- Helper Functions ---
def initialize_session_state():
    """Initializes session state variables."""
    if "user_name" not in st.session_state: st.session_state.user_name = ""
    if "user_email" not in st.session_state: st.session_state.user_email = ""
    if "logged_in" not in st.session_state: st.session_state.logged_in = False
    if "llm" not in st.session_state:
        try:
            st.session_state.llm = llm_handler.get_llm()
        except ValueError as e:
            st.error(f"LLM Initialization Error: {e}. Please ensure GOOGLE_API_KEY is set in .env")
            st.stop()
    
    if "last_interacted_task_details" not in st.session_state:
        st.session_state.last_interacted_task_details = None
    if "chat_history_for_context" not in st.session_state: 
        st.session_state.chat_history_for_context = []

# --- Initialize ---
initialize_session_state()
db.create_db_and_table() 
if "table_info" not in st.session_state or st.session_state.get("reload_table_info", False):
    st.session_state.table_info = db.get_db_info()
    st.session_state.reload_table_info = False


# --- UI Sections ---

if not st.session_state.logged_in:
    st.title("AI Task Manager Login")
    with st.form("login_form"):
        name = st.text_input("Your Name", value=st.session_state.get("user_name_input", ""))
        email = st.text_input("Your Email", value=st.session_state.get("user_email_input", ""))
        login_button = st.form_submit_button("Login")

        if login_button:
            error_messages = []
            if not name:
                error_messages.append("Please enter your name.")
            if not email:
                error_messages.append("Please enter your email.")
            elif not email.strip().lower().endswith(".com"):
                error_messages.append("Invalid email format.")

            if not error_messages:
                st.session_state.user_name = name
                st.session_state.user_email = email
                st.session_state.logged_in = True
                st.session_state.user_name_input = name 
                st.session_state.user_email_input = email
                st.session_state.last_interacted_task_details = None 
                st.session_state.reload_table_info = True
                st.rerun()
            else:
                for msg in error_messages:
                    st.error(msg)
else:
    st.sidebar.header("User Info")
    st.sidebar.write(f"👤 **Name:** {st.session_state.user_name}")
    st.sidebar.write(f"📧 **Email:** {st.session_state.user_email}")
    if st.sidebar.button("Logout"):
        st.session_state.logged_in = False
        st.session_state.user_name = ""
        st.session_state.user_email = ""
        st.session_state.last_interacted_task_details = None
        st.rerun()

    st.title(f"📝 AI Task Manager for {st.session_state.user_name}")
    st.markdown("Enter your task command (e.g., 'I have a meeting at 2pm on next Friday' , 'Show pending tasks').")

    if st.session_state.last_interacted_task_details:
        task_ctx = st.session_state.last_interacted_task_details
        
        # Prepare task context display message
        task_name = task_ctx.get('task_name', 'N/A')
        task_id = task_ctx.get('id', 'N/A')
        due_date = task_ctx.get('due_date', '')
        due_time = task_ctx.get('due_time', '')
        ctx_display = f"Last task: '{task_name}' (ID: {task_id})"
        if due_date:
            ctx_display += f" - Due: {due_date}"
        if due_time:
            ctx_display += f" at {due_time}"
        st.caption(ctx_display)


    user_input_query = st.text_input("Your command:", key="task_input", placeholder="e.g., Add task 'Submit report' due next Friday 3pm category Work")

    if st.button("Process Command", type="primary"):
        if not user_input_query:
            st.warning("Please enter a command.")
        else:
            llm = st.session_state.llm
            table_info = st.session_state.table_info
            
            context_str = "None"
            if st.session_state.last_interacted_task_details:
                details = st.session_state.last_interacted_task_details
                context_list = []
                if details.get('id'): context_list.append(f"id: {details['id']}")
                if details.get('task_name'): context_list.append(f"name: '{details['task_name']}'")
                if details.get('due_date'): context_list.append(f"due_date: {details['due_date']}")
                if details.get('due_time'): context_list.append(f"due_time: {details['due_time']}")
                context_str = f"Task context - {', '.join(context_list)}"


            with st.spinner("🤖 Thinking and generating SQL..."):
                try:
                    generated_sql = llm_handler.generate_sql_query(
                        llm,
                        user_input_query,
                        table_info,
                        st.session_state.user_name,
                        st.session_state.user_email,
                        context_str
                    )
                except Exception as e:
                    st.error(f"Error generating SQL: {e}")
                    generated_sql = None

            if generated_sql:
                st.write("⚙️ **Generated SQL Query:**")
                st.code(generated_sql, language="sql")

                is_select_query = generated_sql.strip().upper().startswith("SELECT")
                is_insert_query = generated_sql.strip().upper().startswith("INSERT")

                with st.spinner("💾 Executing query..."):
                    try:
                        summary_context_for_llm = ""
                        if is_select_query:
                            data, columns = db.execute_select_query(generated_sql)
                            if data:
                                df = pd.DataFrame(data, columns=columns)
                                major_display_columns = ['id', 'task_name', 'status', 'category', 'due_date', 'due_time', 'created_at']
                                display_cols_in_df = [col for col in major_display_columns if col in df.columns]
                                
                                if not display_cols_in_df and df.columns.any():
                                    display_cols_in_df = df.columns.tolist()

                                if display_cols_in_df:
                                    st.dataframe(df[display_cols_in_df], use_container_width=True)
                                else:
                                    st.info("The query ran but returned no columns to display.")
                                
                                summary_context_for_llm = f"Retrieved {len(data)} task(s)."
                                if len(data) == 1: 
                                    st.session_state.last_interacted_task_details = dict(zip(columns, data[0]))
                                elif len(data) == 0:
                                    summary_context_for_llm = "No tasks found matching your criteria."
                            else:
                                st.info("No tasks found matching your criteria.")
                                summary_context_for_llm = "No tasks found matching your criteria."
                                st.session_state.last_interacted_task_details = None 

                        else: 
                            result = db.execute_dml_query(generated_sql)
                            
                            action = "processed"
                            if is_insert_query: 
                                action = "added"
                                if result: 
                                    inserted_task_details = db.get_task_by_id(result, st.session_state.user_email)
                                    if inserted_task_details:
                                        st.session_state.last_interacted_task_details = inserted_task_details
                                        summary_context_for_llm = f"Task '{inserted_task_details.get('task_name')}' (ID: {result}) was {action}."
                                    else:
                                        summary_context_for_llm = f"Task was {action}, but details couldn't be retrieved post-insertion."
                                else:
                                    summary_context_for_llm = f"Task addition was attempted but may not have completed as expected (no ID returned)."
                            elif "UPDATE" in generated_sql.upper(): 
                                action = "updated"
                                summary_context_for_llm = f"Task(s) {action}. {result} row(s) affected."
                            elif "DELETE" in generated_sql.upper(): 
                                action = "deleted"
                                summary_context_for_llm = f"Task(s) {action}. {result} row(s) affected."
                                st.session_state.last_interacted_task_details = None 
                            
                            st.success(f"Task command '{action}' processed successfully.")


                        with st.spinner("📜 Generating friendly summary..."):
                           final_summary = llm_handler.summarize_query_result(
                               llm,
                               user_input_query,
                               generated_sql,
                               summary_context_for_llm
                           )
                        st.markdown(f"**🤖 Summary:**\n {final_summary}")

                    except ValueError as ve:
                         st.error(f"⚠️ Action failed: {ve}")
                    except sqlite3.Error as e: 
                        st.error(f"❌ Database Error: {e}")
                        st.error(f"   Failed Query: {generated_sql}")
                    except Exception as e:
                        st.error(f"❌ An unexpected error occurred: {e}")
                        st.error(f"   Query attempted: {generated_sql}")

            elif not user_input_query.strip() == "":
                st.error("Could not generate an SQL query for your request. Please try rephrasing.")

    st.markdown("---")
    st.markdown("Example commands:")
    st.caption("""
    - Add: "Schedule a 'Team sync meeting' for next Tuesday at 10:00 category Work"
    - Add: "I have a 'Doctor's appointment' tomorrow at 3:30 PM"
    - View: "Show my tasks for this week", "What's pending?"
    - Update: "Mark 'Team sync meeting' as completed" (if it was the last task discussed)
    - Update: "I've finished the 'Doctor's appointment'"
    - Delete: "Cancel the 'Team sync meeting'"
    - Delete: "Remove task 'Old project idea'"
    """)