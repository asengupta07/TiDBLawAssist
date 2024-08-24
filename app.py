import streamlit as st
import sqlite3
from datetime import datetime
from uuid import uuid4
from helper import gen
import hashlib
import PyPDF2
import io
import os

def init_db():
    conn = sqlite3.connect('conversations.db', check_same_thread=False)
    c = conn.cursor()

    # Create users table
    c.execute('''CREATE TABLE IF NOT EXISTS users
                 (id INTEGER PRIMARY KEY AUTOINCREMENT, username TEXT UNIQUE, password TEXT)''')

    # Check if conversations table exists
    c.execute("SELECT name FROM sqlite_master WHERE type='table' AND name='conversations'")
    table_exists = c.fetchone()

    if not table_exists:
        # If the table doesn't exist, create it with all columns including id
        c.execute('''CREATE TABLE conversations
                     (id INTEGER PRIMARY KEY AUTOINCREMENT,
                      session_id TEXT, 
                      timestamp DATETIME, 
                      role TEXT, 
                      content TEXT, 
                      title TEXT, 
                      user_id INTEGER,
                      FOREIGN KEY(user_id) REFERENCES users(id))''')
    else:
        # If the table exists, check for missing columns
        c.execute("PRAGMA table_info(conversations)")
        columns = [column[1] for column in c.fetchall()]
        
        if 'id' not in columns:
            # If 'id' column is missing, we need to recreate the table
            c.execute("ALTER TABLE conversations RENAME TO conversations_old")
            c.execute('''CREATE TABLE conversations
                         (id INTEGER PRIMARY KEY AUTOINCREMENT,
                          session_id TEXT, 
                          timestamp DATETIME, 
                          role TEXT, 
                          content TEXT, 
                          title TEXT, 
                          user_id INTEGER,
                          FOREIGN KEY(user_id) REFERENCES users(id))''')
            c.execute("INSERT INTO conversations (session_id, timestamp, role, content, title, user_id) SELECT session_id, timestamp, role, content, title, user_id FROM conversations_old")
            c.execute("DROP TABLE conversations_old")
        
        if 'title' not in columns:
            c.execute("ALTER TABLE conversations ADD COLUMN title TEXT")
        
        if 'user_id' not in columns:
            c.execute("ALTER TABLE conversations ADD COLUMN user_id INTEGER REFERENCES users(id)")

    conn.commit()
    return conn, c

conn, c = init_db()

def add_id_column():
    c.execute("PRAGMA table_info(conversations)")
    columns = [column[1] for column in c.fetchall()]
    if 'id' not in columns:
        c.execute("ALTER TABLE conversations ADD COLUMN id INTEGER PRIMARY KEY AUTOINCREMENT")
        conn.commit()

add_id_column()

def process_pdf(uploaded_file):
    pdf_reader = PyPDF2.PdfReader(io.BytesIO(uploaded_file.getvalue()))
    text = ""
    for page in pdf_reader.pages:
        text += page.extract_text()
    return text

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

@st.cache_data(ttl=60)
def get_session_list(user_id):
    c.execute("""
        SELECT session_id, 
               COALESCE(MIN(CASE WHEN role = 'system' THEN title END), MIN(title)) as title,
               MAX(timestamp) as last_update
        FROM conversations 
        WHERE user_id = ?
        GROUP BY session_id
        HAVING COUNT(*) > 0
        ORDER BY last_update DESC
    """, (user_id,))
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
    if title and role == "system":
        c.execute("INSERT OR REPLACE INTO conversations (session_id, timestamp, role, content, title, user_id) VALUES (?, ?, ?, ?, ?, ?)",
                  (session_id, datetime.now(), role, content, title, user_id))
    else:
        c.execute("INSERT INTO conversations (session_id, timestamp, role, content, user_id) VALUES (?, ?, ?, ?, ?)",
                  (session_id, datetime.now(), role, content, user_id))
    conn.commit()

def remove_pdf(file_name):
    if file_name in st.session_state.uploaded_files:
        del st.session_state.uploaded_files[file_name]
        return True
    return False

def get_unique_filename(filename):
    name, ext = os.path.splitext(filename)
    counter = 1
    new_filename = filename
    while new_filename in st.session_state.uploaded_files:
        new_filename = f"{name}_{counter}{ext}"
        counter += 1
    return new_filename

def update_conversation_title(session_id, title, user_id):
    c.execute("UPDATE conversations SET title = ? WHERE session_id = ? AND user_id = ?", (title, session_id, user_id))
    conn.commit()
    print(f"Updated title for session {session_id}: {title}") 

@st.cache_data(ttl=60)  # Cache for 60 seconds
def get_session_list(user_id):
    c.execute("""
        SELECT session_id, 
               COALESCE(MIN(CASE WHEN role = 'system' THEN title END), MIN(title)) as title,
               MAX(timestamp) as last_update
        FROM conversations 
        WHERE user_id = ?
        GROUP BY session_id
        HAVING COUNT(*) > 0
        ORDER BY last_update DESC
    """, (user_id,))
    return [(row[0], row[1] or f"Conversation {row[0][:8]}") for row in c.fetchall()]

def delete_conversation(session_id, user_id):
    print(f"Deleting conversation: session_id={session_id}, user_id={user_id}")
    c.execute("DELETE FROM conversations WHERE session_id = ? AND user_id = ?", (session_id, user_id))
    rows_affected = c.rowcount
    print(f"Rows affected: {rows_affected}")
    conn.commit()
    return rows_affected > 0

def load_conversation(session_id, user_id):
    c.execute("SELECT role, content FROM conversations WHERE session_id = ? AND user_id = ? ORDER BY timestamp",
              (session_id, user_id))
    return c.fetchall()

def is_pdf_query(prompt, uploaded_files):
    return any(pdf_name.lower() in prompt.lower() for pdf_name in uploaded_files.keys())

def generate_fallback_title(prompt):
    words = prompt.split()
    return " ".join(words[:3]) + "..." if len(words) > 3 else prompt

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

if 'user_id' in st.session_state:
    # Main app UI (only shown after login)
    st.title(f"TiDB LawAssist - Welcome, {st.session_state.username}")

    # Initialize session state
    if 'session_id' not in st.session_state:
        st.session_state.session_id = str(uuid4())
    if 'messages' not in st.session_state:
        st.session_state.messages = []
    if 'force_sidebar_update' not in st.session_state:
        st.session_state.force_sidebar_update = False
    if 'uploaded_files' not in st.session_state:
        st.session_state.uploaded_files = {}
    if 'file_uploader_key' not in st.session_state:
        st.session_state.file_uploader_key = str(uuid4())

    # Sidebar
    with st.sidebar:
        st.header("About")
        st.write("TiDB LawAssist is an AI-powered legal assistant.")
        st.write("Version 1.0")

        if st.session_state.force_sidebar_update:
            st.session_state.force_sidebar_update = False
            get_session_list.clear()

        session_list = get_session_list(st.session_state.user_id)

        if st.sidebar.button("Start New Conversation"):
            new_session_id = str(uuid4())
            st.session_state.session_id = new_session_id
            st.session_state.messages = []
            new_title = f"Conversation {new_session_id[:8]}"
            save_message(new_session_id, "system", "Conversation started", st.session_state.user_id, title=new_title)
            st.session_state.force_sidebar_update = True
            # Clear uploaded files when starting a new conversation
            st.session_state.uploaded_files = {}
            st.session_state.displayed_warnings = set()
            # Reset the file uploader
            st.session_state.file_uploader_key = str(uuid4())
            st.session_state.show_files_cleared_message = True
            st.rerun()

        st.subheader("Past Conversations")
        if session_list:
            for index, (session_id, title) in enumerate(session_list):
                col1, col2 = st.columns([4, 1])
                with col1:
                    if st.button(title[:20] + '...' if len(title) > 20 else title, key=f"select_{session_id}_{index}"):
                        st.session_state.session_id = session_id
                        st.session_state.messages = load_conversation(session_id, st.session_state.user_id)
                        st.session_state.uploaded_files = {}
                        st.session_state.displayed_warnings = set()
                        st.session_state.show_files_cleared_message = True
                        st.rerun()
                with col2:
                    if st.button("Del", key=f"delete_{session_id}_{index}", help="Delete conversation"):
                        if delete_conversation(session_id, st.session_state.user_id):
                            if session_id == st.session_state.session_id:
                                st.session_state.session_id = str(uuid4())
                                st.session_state.messages = []
                            st.session_state.force_sidebar_update = True
                            get_session_list.clear()
                            st.rerun()
                        else:
                            st.error("Failed to delete conversation.")
        else:
            st.write("No past conversations yet.")
        
        # Logout button
        if st.button("Logout"):
            for key in list(st.session_state.keys()):
                del st.session_state[key]
            st.rerun()

    # Main content
    st.markdown('<div class="main-content">', unsafe_allow_html=True)

    if st.session_state.get('show_files_cleared_message', False):
        st.info("Previous uploaded files have been cleared for this new conversation.")
        st.session_state.show_files_cleared_message = False

    if 'uploaded_files' not in st.session_state:
        st.session_state.uploaded_files = {}
    if 'displayed_warnings' not in st.session_state:
        st.session_state.displayed_warnings = set()
    if 'file_uploader_key' not in st.session_state:
        st.session_state.file_uploader_key = str(uuid4())

    uploaded_files = st.file_uploader("Upload PDF files", type="pdf", accept_multiple_files=True, key=st.session_state.file_uploader_key)
    if uploaded_files:
        for uploaded_file in uploaded_files:
            original_filename = uploaded_file.name
            if original_filename not in st.session_state.uploaded_files:
                pdf_text = process_pdf(uploaded_file)
                st.session_state.uploaded_files[original_filename] = pdf_text
                st.success(f"PDF '{original_filename}' uploaded and processed successfully!")
            else:
                st.info(f"PDF '{original_filename}' is already uploaded.")

    # Clear warnings for files that no longer exist in the uploader
    for filename in list(st.session_state.get('displayed_warnings', set())):
        if filename not in [f.name for f in (uploaded_files or [])]:
            st.session_state.displayed_warnings.discard(filename)

    # Display currently uploaded files
    if st.session_state.uploaded_files:
        st.write("Uploaded files:")
        for file_name in st.session_state.uploaded_files.keys():
            col1, col2 = st.columns([4, 1])
            with col1:
                st.write(f"- {file_name}")
            with col2:
                if st.button("Remove", key=f"remove_{file_name}"):
                    if remove_pdf(file_name):
                        st.success(f"Removed {file_name}")
                        st.rerun()
                    else:
                        st.error(f"Failed to remove {file_name}")

    # Chat container
    for role, content in st.session_state.messages:
        with st.chat_message(role):
            st.markdown(content)

    # Chat input
    if prompt := st.chat_input("What legal question do you have?"):
        st.session_state.messages.append(("user", prompt))
        save_message(st.session_state.session_id, "user", prompt, st.session_state.user_id)
        
        first_message = len(st.session_state.messages) == 1
        
        # Generate and save new title after first user message


        if first_message:
            if is_pdf_query(prompt, st.session_state.uploaded_files):
                pdf_name = next(name for name in st.session_state.uploaded_files.keys() if name.lower() in prompt.lower())
                auto_title = f"{pdf_name}_query"
            else:
                title_prompt = f"Based on this query, generate a short, relevant title (max 5 words): {prompt}"
                auto_title = gen(title_prompt).strip()
                
                # Check if the generated title is inappropriate or too short
                if auto_title.lower().startswith(("i cannot", "unfortunately", "i'm sorry")) or len(auto_title) < 5:
                    auto_title = generate_fallback_title(prompt)
            
            # Final check to ensure we have a valid title
            if not auto_title or len(auto_title) < 3:
                auto_title = f"Conversation_{st.session_state.session_id[:8]}"
            
            update_conversation_title(st.session_state.session_id, auto_title, st.session_state.user_id)
        
        with st.chat_message("user"):
            st.markdown(prompt)

        # Prepare the full query including all uploaded PDF contents
        full_query = "User Question: " + prompt + "\n\n"
        for file_name, content in st.session_state.uploaded_files.items():
            full_query += f"Content of {file_name}:\n{content[:1000]}...\n\n"  # Limit to first 1000 chars per file for brevity

        with st.chat_message("assistant"):
            with st.spinner("Generating response..."):
                response = gen(full_query)
            st.write(response)
        st.session_state.messages.append(("assistant", response))
        save_message(st.session_state.session_id, "assistant", response, st.session_state.user_id)

        if first_message:
            st.session_state.update_sidebar = True
            st.rerun()

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