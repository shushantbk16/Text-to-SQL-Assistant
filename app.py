import streamlit as st
import os
from engine import SQLAgent

# Page Config
st.set_page_config(
    page_title="Text-to-SQL Assistant",
    page_icon="🔍",
    layout="wide"
)

# Title and Description
st.title("🤖 Text-to-SQL Assistant")
st.markdown("""
Ask questions about your E-commerce data (Customers, Products, Orders).
**Example Queries:**
- *Show me the top 5 most expensive products.*
- *How many orders were placed in the North region?*
- *What is the total revenue from Electronics?*
""")

# Load .env if present
from dotenv import load_dotenv
load_dotenv()

# Initialize Agent
# Initialize Agent
if "agent" not in st.session_state:
    # st.write("Debug: Checking API Key...")
    api_key = os.environ.get("GROQ_API_KEY")
    if not api_key:
        st.error("GROQ_API_KEY not found.")
    else:
        try:
            with st.spinner("Initializing AI Agent... (This may take a minute)"):
                st.session_state.agent = SQLAgent(
                    model_name="llama-3.3-70b-versatile",
                    base_url="https://api.groq.com/openai/v1",
                    api_key=api_key
                )
            # st.success("Agent Initialized!")
        except Exception as e:
            st.error(f"Failed to initialize agent: {e}")

# Self-Healing Database Check (Run once on load)
if "db_checked" not in st.session_state:
    import sqlite3
    from setup_db import DB_NAME, create_tables, seed_data
    
    try:
        conn = sqlite3.connect(DB_NAME)
        cursor = conn.cursor()
        cursor.execute("SELECT name FROM sqlite_master WHERE type='table'")
        tables = cursor.fetchall()
        
        if not tables:
            with st.spinner("Database empty. Seeding data..."):
                create_tables(conn)
                seed_data(conn)
            st.success("Database seeded successfully!")
        
        conn.close()
        st.session_state.db_checked = True
    except Exception as e:
        st.error(f"Database check failed: {e}")

# Chat Interface
tab1, tab2 = st.tabs(["💬 Chat", "🗃️ Database Preview"])

with tab1:
    if "messages" not in st.session_state:
        st.session_state.messages = []

    # Display chat history
    for message in st.session_state.messages:
        with st.chat_message(message["role"]):
            st.markdown(message["content"])
            if "sql" in message:
                with st.expander("View SQL & Reasoning"):
                    st.code(message["sql"], language="sql")
                    st.markdown(f"**Reasoning:** {message['reasoning']}")

    # User Input
    if prompt := st.chat_input("What would you like to know?"):
        # Add user message to chat history
        st.session_state.messages.append({"role": "user", "content": prompt})
        with st.chat_message("user"):
            st.markdown(prompt)

        # Generate response
        with st.chat_message("assistant"):
            if not st.session_state.agent.llm:
                 st.error("LLM not initialized. Please configure the provider and API Key in the sidebar.")
            else:
                with st.spinner("Thinking..."):
                    try:
                        response = st.session_state.agent.process_query(prompt)
                        
                        # Check if it's a clarification question
                        if response.get("is_clarification"):
                            st.info(f"🤔 **Clarification Needed:** {response['answer']}")
                            st.session_state.messages.append({
                                "role": "assistant", 
                                "content": response["answer"]
                            })
                        else:
                            st.markdown(response["answer"])
                            
                            # Add assistant message to chat history
                            st.session_state.messages.append({
                                "role": "assistant", 
                                "content": response["answer"],
                                "sql": response["sql"],
                                "reasoning": response["reasoning"]
                            })
                            
                            with st.expander("View SQL & Reasoning"):
                                st.code(response["sql"], language="sql")
                                st.markdown(f"**Reasoning:** {response['reasoning']}")
                            
                    except Exception as e:
                        st.error(f"An error occurred: {e}")

with tab2:
    st.header("Database Schema & Content")
    import sqlite3
    from setup_db import DB_NAME
    
    try:
        conn = sqlite3.connect(DB_NAME)
        cursor = conn.cursor()
        
        # Get all tables
        cursor.execute("SELECT name FROM sqlite_master WHERE type='table'")
        tables = cursor.fetchall()
        
        if tables:
            table_names = [t[0] for t in tables]
            selected_table = st.selectbox("Select Table", table_names)
            
            if selected_table:
                st.subheader(f"Table: {selected_table}")
                
                # Get columns
                cursor.execute(f"PRAGMA table_info({selected_table})")
                columns_info = cursor.fetchall()
                column_names = [col[1] for col in columns_info]
                
                # Get data
                cursor.execute(f"SELECT * FROM {selected_table} LIMIT 10")
                rows = cursor.fetchall()
                
                # Display as a simple table using Streamlit
                # Convert to list of dicts for st.dataframe or just list of lists
                st.write(f"Showing first 10 rows of {selected_table}")
                st.dataframe([dict(zip(column_names, row)) for row in rows])
                
        else:
            st.info("No tables found in the database.")
            
        conn.close()
        
    except Exception as e:
        st.error(f"Error connecting to database: {e}")
