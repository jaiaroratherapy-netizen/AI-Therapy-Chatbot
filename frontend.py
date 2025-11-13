"""
AI Therapy Chatbot - Streamlit Frontend
Updated: Smart resume logic - only creates sessions when user sends first message
"""

import streamlit as st
import requests
from typing import List, Dict, Optional

# ============================================
# Configuration
# ============================================
import os
API_BASE_URL = os.getenv("API_BASE_URL", "http://localhost:8000")
# ============================================
# Page Configuration
# ============================================

st.set_page_config(
    page_title="AI Therapy Practice",
    page_icon="🧠",
    layout="wide",
    initial_sidebar_state="expanded"
)

# ============================================
# Session State Initialization
# ============================================

if "logged_in" not in st.session_state:
    st.session_state.logged_in = False
if "current_user_id" not in st.session_state:
    st.session_state.current_user_id = None
if "current_user_name" not in st.session_state:
    st.session_state.current_user_name = None
if "current_session_id" not in st.session_state:
    st.session_state.current_session_id = None
if "current_session_name" not in st.session_state:
    st.session_state.current_session_name = None
if "messages" not in st.session_state:
    st.session_state.messages = []
if "sessions_list" not in st.session_state:
    st.session_state.sessions_list = []

# ============================================
# API Helper Functions
# ============================================

def check_backend_health() -> bool:
    try:
        response = requests.get(f"{API_BASE_URL}/", timeout=90)
        return response.status_code == 200
    except requests.exceptions.RequestException:
        return False

def create_new_session(email: str, name: str) -> tuple:
    try:
        response = requests.post(
            f"{API_BASE_URL}/sessions/new",
            json={"user_id": email, "name": name},
            timeout=90
        )
        if response.status_code == 200:
            data = response.json()
            return data["session_id"], data["session_name"], None
        else:
            return None, None, f"Error: {response.status_code}"
    except Exception as e:
        return None, None, f"Error: {str(e)}"

def send_message_to_api(user_id: str, session_id: str, message: str) -> tuple:
    try:
        response = requests.post(
            f"{API_BASE_URL}/chat",
            json={"user_id": user_id, "session_id": session_id, "message": message},
            timeout=90
        )
        if response.status_code == 200:
            data = response.json()
            return data["ai_response"], None
        else:
            return None, f"Error: {response.status_code}"
    except Exception as e:
        return None, f"Error: {str(e)}"

def get_user_sessions(user_id: str) -> tuple:
    try:
        response = requests.get(f"{API_BASE_URL}/users/{user_id}/sessions", timeout=90)
        if response.status_code == 200:
            return response.json(), None
        else:
            return [], f"Error: {response.status_code}"
    except Exception as e:
        return [], f"Error: {str(e)}"

def get_conversation(user_id: str, session_id: str) -> tuple:
    try:
        response = requests.get(
            f"{API_BASE_URL}/conversations/{session_id}",
            params={"user_id": user_id},
            timeout=90
        )
        if response.status_code == 200:
            data = response.json()
            return data["messages"], data["session_name"], None
        else:
            return [], None, f"Error: {response.status_code}"
    except Exception as e:
        return [], None, f"Error: {str(e)}"

# ============================================
# Login Screen
# ============================================

def show_login_screen():
    st.title("🧠 AI Therapy Client Simulator")
    st.markdown("### Practice your therapy skills with Pritam, an AI client")
    st.markdown("---")
    
    col1, col2, col3 = st.columns([1, 2, 1])
    
    with col2:
        st.markdown("### Welcome! Please enter your details to begin:")
        
        if not check_backend_health():
            st.error("⚠️ Backend server is not running!")
            st.code("python backend_gemini.py", language="bash")
            return
        
        with st.form("login_form"):
            email = st.text_input("Your Email", placeholder="e.g., john@gmail.com")
            name = st.text_input("Your Name", placeholder="e.g., John Smith")
            submit_button = st.form_submit_button("Start Practicing", use_container_width=True)
            
            if submit_button:
                if not email or not name:
                    st.warning("⚠️ Please enter both email and name")
                    return
                
                if "@" not in email or "." not in email:
                    st.warning("⚠️ Please enter a valid email")
                    return
                
                # Set user info
                st.session_state.logged_in = True
                st.session_state.current_user_id = email.strip().lower()
                st.session_state.current_user_name = name.strip()
                
                # Smart Resume Logic
                with st.spinner("Loading your sessions..."):
                    sessions, error = get_user_sessions(email.strip().lower())
                
                if not error and sessions and len(sessions) > 0:
                    # User has existing sessions
                    latest_session = sessions[0]  # Already sorted by created_at DESC
                    
                    if latest_session["message_count"] > 0:
                        # Last session has messages - load it
                        messages, sess_name, error = get_conversation(
                            email.strip().lower(),
                            latest_session["session_id"]
                        )
                        
                        if not error:
                            st.session_state.current_session_id = latest_session["session_id"]
                            st.session_state.current_session_name = sess_name
                            st.session_state.messages = messages
                            st.success(f"✅ Welcome back, {name}! Resuming {sess_name}")
                        else:
                            # Error loading - start fresh
                            st.session_state.current_session_id = None
                            st.session_state.current_session_name = None
                            st.session_state.messages = []
                    else:
                        # Last session is empty - start fresh
                        st.session_state.current_session_id = None
                        st.session_state.current_session_name = None
                        st.session_state.messages = []
                        st.success(f"✅ Welcome, {name}!")
                else:
                    # First time user or no sessions - start fresh
                    st.session_state.current_session_id = None
                    st.session_state.current_session_name = None
                    st.session_state.messages = []
                    st.success(f"✅ Welcome, {name}!")
                
                st.rerun()

# ============================================
# Chat Screen
# ============================================

def show_chat_screen():
    # ============================================
    # Sidebar
    # ============================================
    
    with st.sidebar:
        st.markdown("### 👤 Current User")
        st.markdown(f"**Name:** {st.session_state.current_user_name}")
        st.markdown(f"**Email:** {st.session_state.current_user_id}")
        st.markdown("---")
        
        st.markdown("### 📚 Your Sessions")
        
        # New Chat Button
        if st.button("➕ New Chat", use_container_width=True):
            # Just reset to None - session will be created when user sends first message
            st.session_state.current_session_id = None
            st.session_state.current_session_name = None
            st.session_state.messages = []
            st.success("✅ Started new chat")
            st.rerun()
        
        # Load sessions list
        sessions, error = get_user_sessions(st.session_state.current_user_id)
        if not error:
            st.session_state.sessions_list = sessions
        
        # Sessions dropdown
        if st.session_state.sessions_list:
            st.markdown("**Sessions**")
            
            session_names = [s["session_name"] for s in st.session_state.sessions_list]
            
            # Find current session index
            try:
                if st.session_state.current_session_name:
                    current_idx = session_names.index(st.session_state.current_session_name)
                else:
                    current_idx = 0
            except (ValueError, AttributeError):
                current_idx = 0
            
            # Dropdown
            selected_session = st.selectbox(
                "Select a session",
                options=session_names,
                index=current_idx,
                key="session_selector",
                label_visibility="collapsed"
            )
            
            # Load Session Button
            if st.button("📂 Load Session", use_container_width=True):
                # Find session_id from session_name
                session_id = None
                for s in st.session_state.sessions_list:
                    if s["session_name"] == selected_session:
                        session_id = s["session_id"]
                        break
                
                if session_id:
                    with st.spinner(f"Loading {selected_session}..."):
                        messages, sess_name, error = get_conversation(
                            st.session_state.current_user_id,
                            session_id
                        )
                    
                    if error:
                        st.error(f"❌ {error}")
                    else:
                        st.session_state.current_session_id = session_id
                        st.session_state.current_session_name = sess_name
                        st.session_state.messages = messages
                        st.success(f"✅ Loaded {sess_name}")
                        st.rerun()
        
        st.markdown("---")
        
        # Logout button
        if st.button("🚪 Logout", use_container_width=True):
            st.session_state.logged_in = False
            st.session_state.current_user_id = None
            st.session_state.current_user_name = None
            st.session_state.current_session_id = None
            st.session_state.current_session_name = None
            st.session_state.messages = []
            st.session_state.sessions_list = []
            st.rerun()
    
    # ============================================
    # Main Chat Area
    # ============================================
    
    st.title("💬 Chat with Pritam")
    st.markdown("*23-year-old from Mumbai University.*")
    
    # Display chat messages
    for msg in st.session_state.messages:
        if msg["role"] == "student":
            with st.chat_message("user", avatar="👨‍⚕️"):
                st.markdown(msg["content"])
        else:
            with st.chat_message("assistant", avatar="🧑"):
                st.markdown(msg["content"])
    
    # Chat input
    user_input = st.chat_input("Type your message as a therapist...")
    
    if user_input:
        # Check if we need to create a session first
        if st.session_state.current_session_id is None:
            # First message - create session now
            with st.spinner("Creating session..."):
                session_id, session_name, error = create_new_session(
                    st.session_state.current_user_id,
                    st.session_state.current_user_name
                )
            
            if error:
                st.error(f"❌ Failed to create session: {error}")
                return
            else:
                st.session_state.current_session_id = session_id
                st.session_state.current_session_name = session_name
        
        # Add user message to display
        st.session_state.messages.append({
            "role": "student",
            "content": user_input,
            "timestamp": ""
        })
        
        # Display user message
        with st.chat_message("user", avatar="👨‍⚕️"):
            st.markdown(user_input)
        
        # Get AI response
        with st.spinner("Pritam is typing..."):
            ai_response, error = send_message_to_api(
                st.session_state.current_user_id,
                st.session_state.current_session_id,
                user_input
            )
        
        if error:
            st.error(f"❌ {error}")
        else:
            # Add AI response
            st.session_state.messages.append({
                "role": "ai",
                "content": ai_response,
                "timestamp": ""
            })
            
            # Display AI response
            with st.chat_message("assistant", avatar="🧑"):
                st.markdown(ai_response)
            
            st.rerun()

# ============================================
# Main App Logic
# ============================================

def main():
    if not st.session_state.logged_in:
        show_login_screen()
    else:
        show_chat_screen()

if __name__ == "__main__":
    main()
