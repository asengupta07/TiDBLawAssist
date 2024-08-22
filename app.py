import streamlit as st
import sqlite3
from datetime import datetime
from uuid import uuid4
from helper import gen

# Initialize SQLite database
conn = sqlite3.connect('conversations.db', check_same_thread=False)
c = conn.cursor()
c.execute('''CREATE TABLE IF NOT EXISTS conversations
             (session_id TEXT, timestamp DATETIME, role TEXT, content TEXT)''')
conn.commit()

st.set_page_config(page_title="TiDB LawAssist", page_icon="⚖", layout="wide")

# Enhanced CSS for better design
st.markdown("""
    <style>
    @import url('https://fonts.googleapis.com/css2?family=Roboto:wght@300;400;700&display=swap');
    
    body {
        background-color: #1E1E1E;
        color: #FFFFFF;
        font-family: 'Roboto', sans-serif;
    }
    .stTextInput > div > div > input {
        background-color: #2E2E2E;
        color: #FFFFFF;
        border: 1px solid #4E4E4E;
        border-radius: 5px;
        padding: 10px;
    }
    .stMarkdown {
        color: #FFFFFF;
    }
    .stButton > button {
        background-color: #FF8C00;
        color: #FFFFFF;
        border: none;
        border-radius: 5px;
        padding: 10px 20px;
        transition: background-color 0.3s;
    }
    .stButton > button:hover {
        background-color: #FFA500;
    }
    .stExpander {
        border-color: #4E4E4E;
        border-radius: 5px;
    }
    h1 {
        color: #FF8C00;
        font-size: 3rem;
        font-weight: 700;
    }
    .chat-container {
        background-color: #2E2E2E;
        border-radius: 10px;
        padding: 20px;
        margin-top: 20px;
    }
    .sidebar {
        background-color: #2E2E2E;
        padding: 20px;
        border-radius: 10px;
    }
    .sidebar h2 {
        color: #FF8C00;
    }
    </style>
    """, unsafe_allow_html=True)

def response_generator(prompt):
    return gen(prompt)

def save_message(session_id, role, content):
    c.execute("INSERT INTO conversations VALUES (?, ?, ?, ?)",
              (session_id, datetime.now(), role, content))
    conn.commit()

def load_conversation(session_id):
    c.execute("SELECT role, content FROM conversations WHERE session_id = ? ORDER BY timestamp",
              (session_id,))
    return c.fetchall()

def get_session_list():
    c.execute("SELECT DISTINCT session_id FROM conversations ORDER BY timestamp DESC")
    return [row[0] for row in c.fetchall()]

# Initialize session state
if 'session_id' not in st.session_state:
    st.session_state.session_id = str(uuid4())
if 'messages' not in st.session_state:
    st.session_state.messages = []

# Sidebar
with st.sidebar:
    # st.markdown('<div class="sidebar">', unsafe_allow_html=True)
    st.header("About")
    st.write("TiDB LawAssist is an AI-powered legal assistant.")
    st.write("Version 1.0")

    if st.button("Start New Conversation"):
        st.session_state.session_id = str(uuid4())
        st.session_state.messages = []
        st.rerun()
    
    st.subheader("Past Conversations")
    session_list = get_session_list()
    if session_list:
        selected_session = st.selectbox("Select a past conversation", ["New Conversation"] + session_list)
        if selected_session == "New Conversation":
            if st.session_state.session_id in session_list:
                st.session_state.session_id = str(uuid4())
                st.session_state.messages = []
                st.rerun()
        elif selected_session and selected_session != st.session_state.session_id:
            st.session_state.session_id = selected_session
            st.session_state.messages = load_conversation(selected_session)
            st.rerun()
    else:
        st.write("No past conversations yet.")
    
    # Feedback section in sidebar
    st.subheader("Feedback")
    feedback = st.selectbox("How would you rate this response?", 
                            ["Select an option", "Excellent", "Good", "Fair", "Poor"])
    if feedback != "Select an option":
        st.write(f"Thank you for your {feedback.lower()} feedback!")
    
    # st.markdown('</div>', unsafe_allow_html=True)

# Main content
st.title("TiDB LawAssist")

# Chat container
# st.markdown('<div class="chat-container">', unsafe_allow_html=True)
for message in st.session_state.messages:
    with st.chat_message(message[0]):
        st.markdown(message[1])
# st.markdown('</div>', unsafe_allow_html=True)

# Chat input
if prompt := st.chat_input("What legal question do you have?"):
    st.session_state.messages.append(("user", prompt))
    save_message(st.session_state.session_id, "user", prompt)
    with st.chat_message("user"):
        st.markdown(prompt)

    with st.chat_message("assistant"):
        with st.spinner("Generating response..."):
            response = response_generator(prompt)
        st.write(response)
    st.session_state.messages.append(("assistant", response))
    save_message(st.session_state.session_id, "assistant", response)

# Instructions
with st.expander("How to use TiDB LawAssist"):
    st.write("1. Type your legal question in the chat input.")
    st.write("2. Our AI will provide a response based on legal knowledge.")
    st.write("3. Continue the conversation for more detailed information.")
    st.write("4. Use 'Start New Conversation' to begin a fresh chat.")
    st.write("5. Select past conversations from the sidebar to review previous chats.")

# Export feature
if st.button("Export Conversation"):
    conversation = "\n".join([f"{m[0]}: {m[1]}" for m in st.session_state.messages])
    st.download_button(
        label="Download Conversation",
        data=conversation,
        file_name=f"tidb_lawassist_conversation_{st.session_state.session_id}.txt",
        mime="text/plain"
    )