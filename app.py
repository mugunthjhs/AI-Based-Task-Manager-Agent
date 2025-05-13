import streamlit as st
import pandas as pd
from datetime import datetime
import database as db
import llm_handler
import sqlite3

st.set_page_config(page_title="AI Task Manager", layout="centered", initial_sidebar_state="collapsed")

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
        except Exception as e:
            st.error(f"An unexpected error occurred during LLM initialization: {e}. Please check your setup and API key.")
            st.stop()
    
    if "last_interacted_task_details" not in st.session_state:
        st.session_state.last_interacted_task_details = None
    if "chat_history_for_context" not in st.session_state: 
        st.session_state.chat_history_for_context = []
    
    if "task_input" not in st.session_state: 
        st.session_state.task_input = ""
    
    if "user_name_input" not in st.session_state: st.session_state.user_name_input = ""
    if "user_email_input" not in st.session_state: st.session_state.user_email_input = ""

def set_task_input_value(command_text):
    """Callback to set the st.session_state.task_input from a quick command."""
    st.session_state.task_input = command_text


initialize_session_state()
db.create_db_and_table() 
if "table_info" not in st.session_state or st.session_state.get("reload_table_info", False):
    st.session_state.table_info = db.get_db_info()
    st.session_state.reload_table_info = False

if not st.session_state.logged_in:
    st.title("AI Based Task Manager Login")
    with st.form("login_form"):
        name = st.text_input("Your Name", value=st.session_state.user_name_input) 
        email = st.text_input("Your Email", value=st.session_state.user_email_input) 
        login_button = st.form_submit_button("Login")

        if login_button:
            error_messages = []
            st.session_state.user_name_input = name
            st.session_state.user_email_input = email

            if not name:
                error_messages.append("Please enter your name.")
            if not email:
                error_messages.append("Please enter your email.")
            elif not ("@" in email and "." in email.split('@')[-1] and len(email.split('@')[-1].split('.')[-1]) > 1):
                error_messages.append("Invalid email format. (e.g., user@example.com)")

            if not error_messages:
                st.session_state.user_name = name
                st.session_state.user_email = email
                st.session_state.logged_in = True
                st.session_state.last_interacted_task_details = None 
                st.session_state.reload_table_info = True
                st.session_state.task_input = ""
                st.rerun()
            else:
                for msg in error_messages:
                    st.error(msg)
else:
    st.sidebar.header("User Info")
    st.sidebar.write(f"👤 **Name:** {st.session_state.user_name}")
    st.sidebar.write(f"📧 **Email:** {st.session_state.user_email}")
    if st.sidebar.button("Logout"):
        keys_to_reset_str = ["user_name", "user_email", "user_name_input", "user_email_input", "task_input"]
        keys_to_reset_none = ["last_interacted_task_details"]
        keys_to_reset_list = ["chat_history_for_context"]
        
        for key in keys_to_reset_str:
             if key in st.session_state: st.session_state[key] = ""
        for key in keys_to_reset_none:
             if key in st.session_state: st.session_state[key] = None
        for key in keys_to_reset_list:
             if key in st.session_state: st.session_state[key] = []
        
        st.session_state.logged_in = False
        st.rerun()

    st.title(f"📝 AI Based Task Manager for {st.session_state.user_name}")
    st.markdown("Enter your task command (e.g., 'I have a meeting at 2pm on next Friday' , 'Show pending tasks').")

    if st.session_state.last_interacted_task_details:
        task_ctx = st.session_state.last_interacted_task_details
        task_name = task_ctx.get('task_name', 'N/A')
        task_id = task_ctx.get('id', 'N/A')
        due_date_val = task_ctx.get('due_date', '')
        due_time_val = task_ctx.get('due_time', '')
        
        ctx_display = f"Context: Last interacted task was '{task_name}' (ID: {task_id})"
        if due_date_val: ctx_display += f" - Due: {due_date_val}"
        if due_time_val: ctx_display += f" at {due_time_val}"
        st.caption(ctx_display)

    command_typed_by_user = st.text_input(
        "Your command:", 
        key="task_input", 
        placeholder="e.g., Add task 'Submit report' due next Friday 3pm category Work"
    )
    
    st.markdown("#### 🔘 Quick Commands")
    quick_commands_dict = {
        "📋 View All Tasks": "Show all my tasks",
        "📆 View This Week": "Show tasks for this week",
        "⏳ View Pending": "Show pending tasks",
        "✅ Mark Last as Done": "Mark the last task as completed",
        "➕ Add Example Task": "I have to attend a 'Project meeting' tomorrow at 10:00 AM.",
        "❌ Delete Last Task": "Delete the last task"
    }

    num_quick_commands = len(quick_commands_dict)
    cols_per_row = 3 if num_quick_commands > 2 else (num_quick_commands if num_quick_commands > 0 else 1)
    quick_command_cols = st.columns(cols_per_row)
    
    col_idx = 6
    for label, cmd_text in quick_commands_dict.items():
        current_col = quick_command_cols[col_idx % cols_per_row]
        current_col.button(
            label, 
            key=f"quick_cmd_{label.replace(' ', '_').lower()}", 
            on_click=set_task_input_value, 
            args=(cmd_text,)
        )
        col_idx +=1
    
    st.markdown("   ") 
    
    if st.button("Process Command", type="primary"):
        command_to_process = st.session_state.task_input 
        
        if not command_to_process.strip():
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
                if details.get('status'): context_list.append(f"status: '{details['status']}'")
                context_str = f"This is the context of the last task interacted with (use it for implicit references like 'this task' or 'the last one'): {', '.join(context_list)}"

            with st.spinner("🤖 Thinking and generating SQL..."):
                try:
                    generated_sql = llm_handler.generate_sql_query(
                        llm, command_to_process, table_info,
                        st.session_state.user_name, st.session_state.user_email, context_str
                    )
                except Exception as e:
                    st.error(f"Error generating SQL: {e}")
                    generated_sql = None 

            if generated_sql:
                st.write("⚙️ **Generated SQL Query:**")
                st.code(generated_sql, language="sql")
                is_select_query = generated_sql.strip().upper().startswith("SELECT")
                is_insert_query = generated_sql.strip().upper().startswith("INSERT")
                action = "processed" 

                with st.spinner("💾 Executing query..."):
                    try:
                        summary_context_for_llm = ""
                        if is_select_query:
                            data, columns = db.execute_select_query(generated_sql)
                            if data:
                                df = pd.DataFrame(data, columns=columns)
                                major_display_columns = ['id', 'task_name', 'status', 'category', 'priority', 'due_date', 'due_time', 'created_at']
                                display_cols_in_df = [col for col in major_display_columns if col in df.columns]
                                if not display_cols_in_df and df.columns.any(): 
                                    display_cols_in_df = df.columns.tolist()
                                if display_cols_in_df:
                                    st.dataframe(df[display_cols_in_df], use_container_width=True)
                                else:
                                    st.info("The query ran but returned no columns to display.")
                                summary_context_for_llm = f"Query executed. Retrieved {len(data)} task(s)."
                                if len(data) == 1: 
                                    st.session_state.last_interacted_task_details = dict(zip(columns, data[0]))
                                elif len(data) == 0:
                                    summary_context_for_llm = "Query executed. No tasks found."
                                else:
                                    st.session_state.last_interacted_task_details = None
                            else:
                                st.info("No tasks found matching your criteria.")
                                summary_context_for_llm = "Query executed. No tasks found."
                                st.session_state.last_interacted_task_details = None 
                        else: 
                            result = db.execute_dml_query(generated_sql) 
                            
                            if is_insert_query: 
                                action = "added"
                                if result:
                                    inserted_task_details = db.get_task_by_id(result, st.session_state.user_email)
                                    if inserted_task_details:
                                        st.session_state.last_interacted_task_details = inserted_task_details
                                        summary_context_for_llm = f"Task '{inserted_task_details.get('task_name')}' (ID: {inserted_task_details.get('id')}) was successfully {action}."
                                    else:
                                        summary_context_for_llm = f"Task was {action} (ID: {result}), but details couldn't be retrieved post-insertion."
                                else:
                                    summary_context_for_llm = f"Task addition was attempted but may not have completed as expected (no ID returned or an error occurred)."
                            elif "UPDATE" in generated_sql.upper(): 
                                action = "updated"
                                summary_context_for_llm = f"Task(s) were {action}. {result if result is not None else 'Unknown number of'} row(s) affected."
                                if st.session_state.last_interacted_task_details and st.session_state.last_interacted_task_details.get('id') and result and result > 0:
                                    refreshed_task = db.get_task_by_id(st.session_state.last_interacted_task_details['id'], st.session_state.user_email)
                                    st.session_state.last_interacted_task_details = refreshed_task if refreshed_task else None
                            elif "DELETE" in generated_sql.upper(): 
                                action = "deleted"
                                summary_context_for_llm = f"Task(s) were {action}. {result if result is not None else 'Unknown number of'} row(s) affected."
                                if result and result > 0 and st.session_state.last_interacted_task_details:
                                     st.session_state.last_interacted_task_details = None
                            
                            st.success(f"Command to '{action}' task(s) processed. { (str(result) + ' ') if result is not None else '' }{('row(s) affected.' if action in ['updated', 'deleted'] and result is not None else '') if not (action == 'added' and result) else '' }")
                            st.session_state.reload_table_info = True 

                        with st.spinner("📜 Generating friendly summary..."):
                            final_summary = llm_handler.summarize_query_result(
                                llm, command_to_process, generated_sql, summary_context_for_llm
                            )
                        st.markdown(f"**🤖 AI Summary:**\n{final_summary}")

                    except ValueError as ve: st.error(f"⚠️ Action failed: {ve}")
                    except sqlite3.Error as e: 
                        st.error(f"❌ Database Error: {e}")
                        st.error(f"Failed Query: {generated_sql}")
                    except Exception as e:
                        st.error(f"❌ An unexpected error occurred during query execution: {e}")
                        st.error(f"Query attempted: {generated_sql if generated_sql else 'No SQL was generated due to prior error.'}")
            elif not command_to_process.strip() == "":
                st.error("Could not generate an SQL query for your request. Please try rephrasing.")
    
    st.markdown("---")
    st.markdown("Example commands:")
    st.caption("""
    - Add: "Schedule a 'Team sync meeting' for next Tuesday at 10:00 category Work"
    - Add: "I have a 'Doctor's appointment' tomorrow at 3:30 PM"
    - View: "Show my tasks for this week", "What's pending?"
    - Update: "Mark 'Team sync meeting' as completed" (if it was the last task discussed)
    - Update: "Change the meeting to 3pm" (referring to the last mentioned task)
    - Update: "Set priority high for task id 5" 
    - Delete: "Cancel the 'Team sync meeting'"
    - Delete: "Remove task 'Old project idea'"
    """)
