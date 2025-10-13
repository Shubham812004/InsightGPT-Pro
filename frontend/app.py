import streamlit as st
import requests
import json
import plotly.io as pio
import os
from jose import jwt

# --- Page Configuration & API Endpoints ---
st.set_page_config(page_title="InsightGPT Pro", page_icon="💡", layout="wide")
API_BASE_URL = os.getenv("API_BASE_URL", "http://127.0.0.1:8000")
TOKEN_URL, GUEST_TOKEN_URL, REGISTER_URL = f"{API_BASE_URL}/token", f"{API_BASE_URL}/guest-token", f"{API_BASE_URL}/register"
QUERY_URL, UPLOAD_URL, REPORT_URL = f"{API_BASE_URL}/query", f"{API_BASE_URL}/upload", f"{API_BASE_URL}/report"
SESSIONS_URL = f"{API_BASE_URL}/sessions"

# --- Custom CSS for Styling ---
st.markdown("""
<style>
    .stApp { background-color: #0E1117; }
    div.stButton > button { background-color: #262730; border: 1px solid #6c63ff; }
</style>
""", unsafe_allow_html=True)

# --- Session State Initialization ---
for key, value in {
    'logged_in': False, 'token': "", 'chat_history': [], 'document_name': None,
    'is_guest': False, 'current_session_id': None, 'past_sessions': []
}.items():
    if key not in st.session_state:
        st.session_state[key] = value

def handle_query_submission(query):
    """A centralized function to handle the query submission and API call."""
    st.session_state.chat_history.append({"role": "user", "content": query})
    with st.chat_message("user"): st.markdown(query)
    with st.chat_message("assistant"):
        with st.spinner("Thinking..."):
            headers = {"Authorization": f"Bearer {st.session_state.token}"}
            payload = {"query": query}
            try:
                response = requests.post(QUERY_URL, headers=headers, json=payload)
                if response.status_code == 200:
                    api_response = response.json()
                    answer, chart_json = api_response.get("answer"), api_response.get("chart_json")
                    st.markdown(answer)
                    assistant_message = {"role": "assistant", "content": answer}
                    if chart_json:
                        fig = pio.from_json(chart_json)
                        st.plotly_chart(fig, use_container_width=True)
                        assistant_message["chart"] = chart_json
                    st.session_state.chat_history.append(assistant_message)
                    if not st.session_state.is_guest:
                        if st.session_state.current_session_id:
                            requests.put(f"{SESSIONS_URL}/{st.session_state.current_session_id}", headers=headers, json={"chat_history": st.session_state.chat_history})
                        else:
                            creation_response = requests.post(SESSIONS_URL, headers=headers, json={"chat_history": st.session_state.chat_history})
                            if creation_response.status_code == 200:
                                st.session_state.current_session_id = creation_response.json().get("session_id")
                else:
                    error_text = f"Error: {response.status_code} - {response.text}"
                    st.error(error_text)
                    st.session_state.chat_history.append({"role": "assistant", "content": error_text})
            except requests.exceptions.RequestException as e:
                error_text = f"Connection to backend failed: {e}"
                st.error(error_text)
                st.session_state.chat_history.append({"role": "assistant", "content": error_text})

def process_document_callback():
    uploaded_file = st.session_state.get("pdf_uploader")
    if uploaded_file is None: return
    with st.spinner(f"Processing '{uploaded_file.name}'..."):
        headers = {"Authorization": f"Bearer {st.session_state.token}"}
        files = {'file': (uploaded_file.name, uploaded_file, 'application/pdf')}
        try:
            response = requests.post(UPLOAD_URL, headers=headers, files=files)
            if response.status_code == 200:
                st.session_state.document_name = uploaded_file.name
                st.toast(f"✅ Successfully processed '{uploaded_file.name}'!")
            else:
                st.error(f"Failed to process document. Status: {response.status_code}")
                st.json(response.json())
        except requests.exceptions.RequestException as e:
            st.error(f"Connection to backend failed: {e}")

def show_login_page():
    st.title("💡 Welcome to InsightGPT Pro")
    st.markdown("Your AI-powered data intelligence system.")
    st.divider()
    login_tab, signup_tab = st.tabs(["Login", "Sign Up"])
    with login_tab:
        with st.form("login_form"):
            st.markdown("### Log In to Your Account")
            username = st.text_input("Username", key="login_username")
            password = st.text_input("Password", type="password", key="login_password")
            submitted = st.form_submit_button("Login")
            if submitted:
                form_data = {'username': username, 'password': password}
                try:
                    response = requests.post(TOKEN_URL, data=form_data)
                    if response.status_code == 200:
                        token_data = response.json(); st.session_state.token = token_data.get("access_token"); st.session_state.logged_in = True
                        st.session_state.chat_history = []; st.session_state.document_name = None; st.session_state.is_guest = False; st.session_state.current_session_id = None; st.rerun()
                    else: st.error("Login failed. Check your credentials.")
                except requests.exceptions.RequestException: st.error("Could not connect to the backend.")
        st.divider()
        if st.button("Continue as Guest"):
            try:
                response = requests.post(GUEST_TOKEN_URL)
                if response.status_code == 200:
                    token_data = response.json(); st.session_state.token = token_data.get("access_token"); st.session_state.logged_in = True
                    st.session_state.chat_history = []; st.session_state.document_name = None; st.session_state.is_guest = True; st.session_state.current_session_id = None; st.rerun()
                else: st.error("Could not start guest session.")
            except requests.exceptions.RequestException: st.error("Could not connect to the backend.")
    with signup_tab:
        with st.form("signup_form"):
            st.markdown("### Create a New Account")
            new_username = st.text_input("Choose a Username", key="signup_username")
            new_password = st.text_input("Choose a Password", type="password", key="signup_password")
            signup_submitted = st.form_submit_button("Sign Up")
            if signup_submitted:
                payload = {"username": new_username, "password": new_password}
                try:
                    response = requests.post(REGISTER_URL, json=payload)
                    if response.status_code == 201: st.success("Account created! Please log in.")
                    elif response.status_code == 400: st.error("Username already exists.")
                    else: st.error(f"An error occurred: {response.text}")
                except requests.exceptions.RequestException: st.error("Could not connect to the backend.")

def show_main_app():
    headers = {"Authorization": f"Bearer {st.session_state.token}"}
    
    def start_new_chat():
        st.session_state.chat_history = []
        st.session_state.current_session_id = None
    
    def load_session(session_id):
        try:
            response = requests.get(f"{SESSIONS_URL}/{session_id}", headers=headers)
            if response.status_code == 200:
                st.session_state.chat_history = response.json()
                st.session_state.current_session_id = session_id
            else: st.error("Failed to load session.")
        except requests.exceptions.RequestException: st.error("Connection error.")

    with st.sidebar:
        if st.session_state.is_guest:
            st.markdown("#### 👋 Welcome, **Guest**!")
        else:
            st.markdown(f"#### 👋 Welcome, **{st.session_state.get('username', 'User')}**!")
        
        if st.button("Logout", use_container_width=True):
            st.session_state.logged_in = False
            st.session_state.token = ""
            st.rerun()
        
        st.divider()

        st.button("➕ New Chat", on_click=start_new_chat, use_container_width=True)

        with st.expander("📜 Past Conversations"):
            if not st.session_state.is_guest:
                try:
                    response = requests.get(SESSIONS_URL, headers=headers)
                    if response.status_code == 200:
                        st.session_state.past_sessions = response.json()
                        for session in st.session_state.past_sessions:
                            if st.button(session['title'], key=session['id'], use_container_width=True):
                                load_session(session['id'])
                    else:
                        st.caption("Could not load history.")
                except requests.exceptions.RequestException:
                    st.error("Connection error.")
            else:
                st.caption("Log in to see past conversations.")
        
        with st.expander("📄 Document Analysis", expanded=True):
            st.file_uploader("Upload a PDF to analyze", type="pdf", key="pdf_uploader", on_change=process_document_callback)
            if st.session_state.document_name:
                st.success(f"Active doc: **{st.session_state.document_name}**")
        
        with st.expander("📥 Reporting"):
            if st.session_state.is_guest:
                st.caption("Log in to generate reports.")
            elif st.session_state.chat_history:
                try:
                    report_response = requests.post(REPORT_URL, headers=headers, json={"chat_history": st.session_state.chat_history})
                    if report_response.status_code == 200:
                        st.download_button(label="Download Report", data=report_response.content, file_name="InsightGPT_Report.pdf", mime="application/pdf", use_container_width=True)
                except requests.exceptions.RequestException:
                    st.error("Report connection failed.")
            else:
                st.caption("Start a conversation to generate a report.")

    if not st.session_state.chat_history:
        st.title("💡 InsightGPT Pro")
        st.markdown("Your AI-powered data intelligence system. Start by uploading a document in the sidebar or ask a question about the pre-loaded sales data.")
        st.divider()
        st.markdown("### Example Questions:")
        
        col1, col2 = st.columns(2)
        with col1:
            if st.button("What were the total sales by region?", use_container_width=True):
                handle_query_submission("What were the total sales by region?")
            if st.button("Show me a pie chart of revenue by product.", use_container_width=True):
                handle_query_submission("Show me a pie chart of revenue by product.")
        with col2:
            if st.button("Who sold the most units?", use_container_width=True):
                handle_query_submission("Who sold the most units?")
            if st.button("What did the CEO say in the quarterly report?", use_container_width=True):
                handle_query_submission("What did the CEO say in the quarterly report?")
    else:
        # This just provides a title for ongoing chats
        st.title("💡 InsightGPT Pro")
        st.divider()
        for message in st.session_state.chat_history:
            with st.chat_message(message["role"]):
                st.markdown(message["content"])
                if "chart" in message:
                    try:
                        fig = pio.from_json(message["chart"])
                        st.plotly_chart(fig, use_container_width=True)
                    except (ValueError, json.JSONDecodeError):
                        st.error("Failed to display chart.")

    if user_query := st.chat_input("Ask a question..."):
        handle_query_submission(user_query)

if st.session_state.logged_in:
    if not st.session_state.is_guest:
        st.session_state.username = jwt.decode(st.session_state.token, key=None, options={"verify_signature": False}).get("sub")
    show_main_app()
else:
    show_login_page()
