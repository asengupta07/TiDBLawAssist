import streamlit as st
from helper import gen

st.set_page_config(page_title="TiDB LawAssist", page_icon="⚖️", layout="centered")

# Custom CSS for dark mode
st.markdown("""
    <style>
    body {
        background-color: #1E1E1E;
        color: #FFFFFF;
    }
    .stTextInput > div > div > input {
        background-color: #2E2E2E;
        color: #FFFFFF;
    }
    .stMarkdown {
        color: #FFFFFF;
    }
    .stButton > button {
        background-color: #4E4E4E;
        color: #FFFFFF;
    }
    .stButton > button:hover {
        background-color: #5E5E5E;
    }
    .stExpander {
        border-color: #4E4E4E;
    }
    </style>
    """, unsafe_allow_html=True)

def response_generator(prompt):
    return gen(prompt)

st.title("TiDB LawAssist")

if "messages" not in st.session_state:
    st.session_state.messages = []

for message in st.session_state.messages:
    with st.chat_message(message["role"]):
        st.markdown(message["content"])

if prompt := st.chat_input("What legal question do you have?"):
    st.session_state.messages.append({"role": "user", "content": prompt})
    with st.chat_message("user"):
        st.markdown(prompt)

    with st.chat_message("assistant"):
        with st.spinner("Generating response..."):
            response = response_generator(prompt)
        st.write(response)
    st.session_state.messages.append({"role": "assistant", "content": response})

with st.sidebar:
    st.header("About")
    st.write("TiDB LawAssist is an AI-powered legal assistant.")
    st.write("Version 2.1")
    if st.button("Clear Conversation"):
        st.session_state.messages = []
        st.rerun()

with st.expander("How to use TiDB LawAssist"):
    st.write("1. Type your legal question in the chat input.")
    st.write("2. Our AI will provide a response based on legal knowledge.")
    st.write("3. Continue the conversation for more detailed information.")