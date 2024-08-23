import streamlit as st
import sqlite3
from datetime import datetime
from uuid import uuid4
from helper import gen
import hashlib

# Initialize SQLite database
conn = sqlite3.connect('conversations.db', check_same_thread=False)
c = conn.cursor()

# Create users table
c.execute('''CREATE TABLE IF NOT EXISTS users
             (id INTEGER PRIMARY KEY AUTOINCREMENT, username TEXT UNIQUE, password TEXT)''')

# Check if conversations table exists
c.execute("SELECT name FROM sqlite_master WHERE type='table' AND name='conversations'")
table_exists = c.fetchone()

if not table_exists:
    # If the table doesn't exist, create it with all columns
    c.execute('''CREATE TABLE conversations
                 (session_id TEXT, timestamp DATETIME, role TEXT, content TEXT, title TEXT, user_id INTEGER,
                 FOREIGN KEY(user_id) REFERENCES users(id))''')
else:
    # If the table exists, check for missing columns and add them if necessary
    existing_columns = [column[1] for column in c.execute("PRAGMA table_info(conversations)").fetchall()]
    
    if 'title' not in existing_columns:
        c.execute("ALTER TABLE conversations ADD COLUMN title TEXT")
    
    if 'user_id' not in existing_columns:
        c.execute("ALTER TABLE conversations ADD COLUMN user_id INTEGER REFERENCES users(id)")

conn.commit()


def hash_password(password):
    return hashlib.sha256(password.encode()).hexdigest()

def create_user(username, password):
    hashed_password = hash_password(password)
    try:
        c.execute("INSERT INTO users (username, password) VALUES (?, ?)", (username, hashed_password))
        conn.commit()
        return True
    except sqlite3.IntegrityError:
        return False

def authenticate_user(username, password):
    hashed_password = hash_password(password)
    c.execute("SELECT id FROM users WHERE username = ? AND password = ?", (username, hashed_password))
    result = c.fetchone()
    return result[0] if result else None

# Modify existing functions to include user_id
def save_message(session_id, role, content, user_id, title=None):
    if title:
        c.execute("UPDATE conversations SET title = ? WHERE session_id = ? AND user_id = ?", (title, session_id, user_id))
    c.execute("INSERT INTO conversations (session_id, timestamp, role, content, user_id) VALUES (?, ?, ?, ?, ?)",
              (session_id, datetime.now(), role, content, user_id))
    conn.commit()

def update_conversation_title(session_id, title, user_id):
    c.execute("UPDATE conversations SET title = ? WHERE session_id = ? AND user_id = ?", (title, session_id, user_id))
    conn.commit()

def get_session_list(user_id):
    c.execute("SELECT DISTINCT session_id, title FROM conversations WHERE user_id = ? ORDER BY timestamp DESC", (user_id,))
    return [(row[0], row[1] or f"Conversation {row[0][:8]}") for row in c.fetchall()]

def delete_conversation(session_id, user_id):
    c.execute("DELETE FROM conversations WHERE session_id = ? AND user_id = ?", (session_id, user_id))
    conn.commit()

def load_conversation(session_id, user_id):
    c.execute("SELECT role, content FROM conversations WHERE session_id = ? AND user_id = ? ORDER BY timestamp",
              (session_id, user_id))
    return c.fetchall()

st.set_page_config(page_title="TiDB LawAssist", page_icon="⚖", layout="centered")

# CSS for both light and dark modes
st.markdown("""
<style>
@import url('https://fonts.googleapis.com/css2?family=Roboto:wght@300;400;700&display=swap');

/* Light mode styles */
.light-mode {
    --bg-color: #FFFFFF;
    --text-color: #333333;
    --sidebar-bg: #F0F2F6;
    --input-bg: #FFFFFF;
    --input-border: #CCCCCC;
    --button-bg: #FF8C00;
    --button-text: #FFFFFF;
    --expander-border: #E0E0E0;
}

/* Dark mode styles */
.dark-mode {
    --bg-color: #1E1E1E;
    --text-color: #FFFFFF;
    --sidebar-bg: #2E2E2E;
    --input-bg: #3E3E3E;
    --input-border: #4E4E4E;
    --button-bg: #FF8C00;
    --button-text: #1E1E1E;
    --expander-border: #4E4E4E;
}

.dark-mode .stApp {
    background-color: var(--bg-color) !important;
}

.dark-mode .main .block-container {
    background-color: var(--bg-color) !important;
}

.dark-mode .streamlit-expanderHeader {
    background-color: var(--sidebar-bg) !important;
    color: var(--text-color) !important;
}

.dark-mode .streamlit-expanderContent {
    background-color: var(--bg-color) !important;
    color: var(--text-color) !important;
}

.dark-mode .stTextInput > div > div > input {
    background-color: var(--input-bg) !important;
    color: var(--text-color) !important;
}

.dark-mode .stSelectbox > div > div > div {
    background-color: var(--input-bg) !important;
    color: var(--text-color) !important;
}

body {
    font-family: 'Roboto', sans-serif;
    color: var(--text-color);
}

.sidebar .sidebar-content {
    background-color: var(--sidebar-bg);
}

h1 {
    color: #FF8C00;
    font-size: 3rem;
    font-weight: 700;
}

.stButton > button {
    width: 100%;
    white-space: nowrap;
    overflow: hidden;
    text-overflow: ellipsis;
}

.stButton > button:hover {
    background-color: #FFA500;
}

.chat-container {
    background-color: var(--sidebar-bg);
    border-radius: 10px;
    padding: 20px;
    margin-top: 20px;
}
.stButton > button {
    width: 100%;
    box-sizing: border-box;
}

</style>
""", unsafe_allow_html=True)

def toggle_mode():
    if 'dark_mode' not in st.session_state:
        st.session_state.dark_mode = False
    st.session_state.dark_mode = not st.session_state.dark_mode
    st.rerun()

# Apply the appropriate mode
if 'dark_mode' not in st.session_state:
    st.session_state.dark_mode = False

st.markdown(f"<body class='{'dark-mode' if st.session_state.dark_mode else 'light-mode'}''>", unsafe_allow_html=True)

# User authentication functions
def hash_password(password):
    return hashlib.sha256(password.encode()).hexdigest()

def create_user(username, password):
    hashed_password = hash_password(password)
    try:
        c.execute("INSERT INTO users (username, password) VALUES (?, ?)", (username, hashed_password))
        conn.commit()
        return True
    except sqlite3.IntegrityError:
        return False

def authenticate_user(username, password):
    hashed_password = hash_password(password)
    c.execute("SELECT id FROM users WHERE username = ? AND password = ?", (username, hashed_password))
    result = c.fetchone()
    return result[0] if result else None

def response_generator(prompt):
    return gen(prompt)

def save_message(session_id, role, content, user_id, title=None):
    if title:
        c.execute("UPDATE conversations SET title = ? WHERE session_id = ? AND user_id = ?", (title, session_id, user_id))
    c.execute("INSERT INTO conversations (session_id, timestamp, role, content, user_id) VALUES (?, ?, ?, ?, ?)",
              (session_id, datetime.now(), role, content, user_id))
    conn.commit()

def update_conversation_title(session_id, title, user_id):
    c.execute("UPDATE conversations SET title = ? WHERE session_id = ? AND user_id = ?", (title, session_id, user_id))
    conn.commit()

def get_session_list(user_id):
    c.execute("SELECT DISTINCT session_id, title FROM conversations WHERE user_id = ? ORDER BY timestamp DESC", (user_id,))
    return [(row[0], row[1] or f"Conversation {row[0][:8]}") for row in c.fetchall()]

def delete_conversation(session_id, user_id):
    c.execute("DELETE FROM conversations WHERE session_id = ? AND user_id = ?", (session_id, user_id))
    conn.commit()

def load_conversation(session_id, user_id):
    c.execute("SELECT role, content FROM conversations WHERE session_id = ? AND user_id = ? ORDER BY timestamp",
              (session_id, user_id))
    return c.fetchall()

# User authentication UI
if 'user_id' not in st.session_state:
    st.title("TiDB LawAssist - Login")
    username = st.text_input("Username")
    password = st.text_input("Password", type="password")
    col1, col2 = st.columns([1, 1]) 
    with col1:
        if st.button("Login"):
            user_id = authenticate_user(username, password)
            if user_id:
                st.session_state.user_id = user_id
                st.session_state.username = username
                st.rerun()
            else:
                st.error("Invalid username or password")
    with col2:
        if st.button("Create Account"):
            if create_user(username, password):
                st.success("Account created successfully. Please log in.")
            else:
                st.error("Username already exists")
else:
    # Main app UI (only shown after login)
    st.title(f"TiDB LawAssist - Welcome, {st.session_state.username}")

    # Initialize session state
    if 'session_id' not in st.session_state:
        st.session_state.session_id = str(uuid4())
    if 'messages' not in st.session_state:
        st.session_state.messages = []

    # Sidebar
    with st.sidebar:
        st.header("About")
        st.write("TiDB LawAssist is an AI-powered legal assistant.")
        st.write("Version 1.0")

        if st.button("Start New Conversation"):
            st.session_state.session_id = str(uuid4())
            st.session_state.messages = []
            st.rerun()
        
        st.subheader("Past Conversations")
        session_list = get_session_list(st.session_state.user_id)
        if session_list:
            for session_id, title in session_list:
                col1, col2 = st.columns([4, 1])
                with col1:
                    if st.button(title[:20] + '...' if len(title) > 20 else title, key=f"select_{session_id}"):
                        st.session_state.session_id = session_id
                        st.session_state.messages = load_conversation(session_id, st.session_state.user_id)
                        st.rerun()
                with col2:
                    if st.button("Del", key=f"delete_{session_id}", help="Delete conversation"):
                        delete_conversation(session_id, st.session_state.user_id)
                        if session_id == st.session_state.session_id:
                            st.session_state.session_id = str(uuid4())
                            st.session_state.messages = []
                        st.rerun()
        else:
            st.write("No past conversations yet.")
        
        # Feedback section in sidebar
        st.subheader("Feedback")
        feedback = st.selectbox("How would you rate this response?", 
                                ["Select an option", "Excellent", "Good", "Fair", "Poor"])
        if feedback != "Select an option":
            st.write(f"Thank you for your {feedback.lower()} feedback!")
        
        # Logout button
        if st.button("Logout"):
            del st.session_state.user_id
            del st.session_state.username
            st.rerun()

    # Main content
    st.markdown('<div class="main-content">', unsafe_allow_html=True)

    # Chat container
    for message in st.session_state.messages:
        with st.chat_message(message[0]):
            st.markdown(message[1])

    # Chat input
    if prompt := st.chat_input("What legal question do you have?"):
        st.session_state.messages.append(("user", prompt))
        save_message(st.session_state.session_id, "user", prompt, st.session_state.user_id)
        with st.chat_message("user"):
            st.markdown(prompt)

        # Ask for title before generating response
        title = st.text_input("Give this conversation a title (optional):", key="title_input")
        if title:
            update_conversation_title(st.session_state.session_id, title, st.session_state.user_id)

        with st.chat_message("assistant"):
            with st.spinner("Generating response..."):
                response = response_generator(prompt)
            st.write(response)
        st.session_state.messages.append(("assistant", response))
        save_message(st.session_state.session_id, "assistant", response, st.session_state.user_id)

    if st.session_state.get("title_input"):
        update_conversation_title(st.session_state.session_id, st.session_state.title_input, st.session_state.user_id)

    # Export feature
    if st.button("Export Conversation"):
        conversation = "\n".join([f"{m[0]}: {m[1]}" for m in st.session_state.messages])
        st.download_button(
            label="Download Conversation",
            data=conversation,
            file_name=f"tidb_lawassist_conversation_{st.session_state.session_id}.txt",
            mime="text/plain"
        )

    st.markdown('</div>', unsafe_allow_html=True)