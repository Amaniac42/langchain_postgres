import streamlit as st
import langchain
import time

# Langchain things
def process_document(uploaded_file):
    pass

def get_rag_chain_stream(retreiver, question):
    pass

# Streamlit things
st.title("Qusestion Answering Agent")
st.markdown()

if "messages" not in st.session_state:
    st.session_state.messages = []
if "retriever" not in st.session_state:
    st.session_state.retriever = None
if "document_processed" not in st.session_state:
    st.session_state.document_processed = False

# Sidebar for file upload
with st.sidebar:
    st.header("1. Upload Your Document")
    uploaded_file = st.file_uploader("Upload a PDF file", type=["pdf"])

    if uploaded_file and not st.session_state.document_processed:
        with st.spinner("Processing document..."):
            st.session_state.retriever = process_document(uploaded_file)
        if st.session_state.retriever:
            st.success("Document processed successfully!")
            st.info("You can now ask questions in the main chat area.")

# Display chat messages from history
for message in st.session_state.messages:
    with st.chat_message(message["role"]):
        st.markdown(message["content"])

# Main chat interface
st.header("2. Ask a Question")

if prompt := st.chat_input("What is this document about?"):
    with st.chat_message("user"):
        st.markdown(prompt)
    st.session_state.messages.append({"role": "user", "content": prompt})

    if st.session_state.retriever:
        with st.chat_message("assistant"):
            response_stream = get_rag_chain_stream(st.session_state.retriever, prompt)
            full_response = st.write_stream(response_stream)
        st.session_state.messages.append({"role": "assistant", "content": full_response})
    else:
        with st.chat_message("assistant"):
            st.warning("Please upload and process a document in the sidebar first!")
