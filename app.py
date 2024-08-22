import streamlit as st
from helper import gen 


def response_generator(prompt):
    return gen(prompt)


st.title("TiDB LawAssist")

if "messages" not in st.session_state:
    st.session_state.messages = []

for message in st.session_state.messages:
    with st.chat_message(message["role"]):
        st.markdown(message["content"])

# Accept user input
if prompt := st.chat_input("What is up?"):
    st.session_state.messages.append({"role": "user", "content": prompt})
    with st.chat_message("user"):
        st.markdown(prompt)

    with st.chat_message("assistant"):
        response = st.write(response_generator(prompt))
    st.session_state.messages.append({"role": "assistant", "content": response})