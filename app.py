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

# Initialize Agent with Hardcoded Groq Configuration
if "agent" not in st.session_state:
    api_key = os.environ.get("GROQ_API_KEY")
    if not api_key:
        st.error("GROQ_API_KEY not found in environment variables.")
    else:
        st.session_state.agent = SQLAgent(
            model_name="llama-3.3-70b-versatile",
            base_url="https://api.groq.com/openai/v1",
            api_key=api_key
        )


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
    import pandas as pd
    from setup_db import DB_NAME
    
    try:
        conn = sqlite3.connect(DB_NAME)
        
        # Get all tables
        tables = pd.read_sql("SELECT name FROM sqlite_master WHERE type='table'", conn)
        
        if not tables.empty:
            selected_table = st.selectbox("Select Table", tables["name"].tolist())
            
            if selected_table:
                st.subheader(f"Table: {selected_table}")
                df = pd.read_sql(f"SELECT * FROM {selected_table} LIMIT 50", conn)
                st.dataframe(df)
                st.caption(f"Showing first {len(df)} rows.")
        else:
            st.info("No tables found in the database.")
            
        conn.close()
    except Exception as e:
        st.error(f"Error connecting to database: {e}")
