"""
AI Therapy Chatbot - FastAPI Backend with Gemini 2.0 Flash
Connected to Supabase PostgreSQL Database
Supports both email and name inputs
"""

from typing import Optional, List, Dict
from pydantic import BaseModel
from fastapi import FastAPI, HTTPException
from datetime import datetime
import os
import google.generativeai as genai
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

# Import our database functions
from database import (
    get_or_create_student,
    create_session,
    save_message,
    get_conversation_history,
    get_user_sessions,
    session_exists,
    get_session_name,
    test_connection
)

# Import Pritam's system prompt
from prompts import get_system_prompt

# ============================================
# Initialize FastAPI App
# ============================================
app = FastAPI(title="AI Therapy Chatbot API (Gemini)", version="3.0.0")

# ============================================
# Initialize Gemini Client
# ============================================
genai.configure(api_key=os.environ.get("GEMINI_API_KEY"))

# ============================================
# Pydantic Models
# ============================================

class ChatRequest(BaseModel):
    user_id: str  # Email
    session_id: str
    message: str

class ChatResponse(BaseModel):
    session_id: str
    ai_response: str
    timestamp: str

class NewSessionRequest(BaseModel):
    user_id: str  # Email
    name: str     # Name added here

class NewSessionResponse(BaseModel):
    session_id: str
    session_name: str

class SessionInfo(BaseModel):
    session_id: str
    session_name: str
    created_at: str
    message_count: int

class Message(BaseModel):
    role: str
    content: str
    timestamp: str

class ConversationResponse(BaseModel):
    session_id: str
    session_name: str
    messages: List[Message]

# ============================================
# Helper Function: Convert to Gemini Format
# ============================================

def convert_to_gemini_format(history: List[Dict]) -> List[Dict]:
    """
    Convert database message history to Gemini format
    
    Args:
        history: List of messages from database with 'role' and 'content'
    
    Returns:
        List formatted for Gemini API
    """
    gemini_messages = []
    
    for msg in history:
        # Convert role names
        role = "model" if msg["role"] == "assistant" else "user"
        
        # Convert to Gemini format with 'parts'
        gemini_messages.append({
            "role": role,
            "parts": [{"text": msg["content"]}]
        })
    
    return gemini_messages

# ============================================
# API Endpoints
# ============================================

@app.get("/")
def root():
    """Health check endpoint"""
    return {
        "message": "AI Therapy Chatbot API is running with Gemini 2.0 Flash!",
        "version": "3.0.0",
        "model": "gemini-2.0-flash",
        "status": "healthy",
        "database": "connected"
    }

@app.post("/chat", response_model=ChatResponse)
def chat(request: ChatRequest):
    """
    Main chat endpoint - Send message and get AI response
    Now uses Gemini 2.0 Flash instead of Groq
    """
    
    # Validate session exists
    if not session_exists(request.session_id):
        raise HTTPException(status_code=404, detail="Session not found")
    
    # Get conversation history from database
    history = get_conversation_history(request.session_id)
    
    # Get Pritam's system prompt
    system_prompt = get_system_prompt()
    
    # Initialize Gemini model with system instruction
    model = genai.GenerativeModel(
        'gemini-2.0-flash',
        system_instruction=system_prompt
    )
    
    # Convert history to Gemini format
    gemini_messages = convert_to_gemini_format(history)
    
    # Add current user message
    gemini_messages.append({
        "role": "user",
        "parts": [{"text": request.message}]
    })
    
    # Call Gemini API
    try:
        # Start a chat with history
        chat = model.start_chat(history=gemini_messages[:-1])  # All except last message
        
        # Send the current message
        response = chat.send_message(gemini_messages[-1]["parts"][0]["text"])
        
        ai_response = response.text
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Gemini API error: {str(e)}")
    
    # Save both messages to database
    save_message(request.session_id, "user", request.message)
    save_message(request.session_id, "assistant", ai_response)
    
    # Return response
    return ChatResponse(
        session_id=request.session_id,
        ai_response=ai_response,
        timestamp=datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    )

@app.post("/sessions/new", response_model=NewSessionResponse)
def create_new_session(request: NewSessionRequest):
    """
    Create a new chat session for a user
    Accepts both email and name
    """
    
    # Get or create student with provided email and name
    student_id = get_or_create_student(
        email=request.user_id,
        name=request.name
    )
    
    # Create new session
    session_id, session_name = create_session(student_id, "Pritam")
    
    return NewSessionResponse(
        session_id=session_id,
        session_name=session_name
    )

@app.get("/users/{user_id}/sessions", response_model=List[SessionInfo])
def get_sessions_for_user(user_id: str):
    """
    Get all sessions for a user
    Retrieves from Supabase database
    """
    
    sessions = get_user_sessions(user_id)
    
    return [
        SessionInfo(
            session_id=s["session_id"],
            session_name=s["session_name"],
            created_at=s["created_at"],
            message_count=s["message_count"]
        )
        for s in sessions
    ]

@app.get("/conversations/{session_id}", response_model=ConversationResponse)
def get_conversation(session_id: str, user_id: str):
    """
    Get full conversation for a specific session
    Retrieves from Supabase database
    """
    
    # Validate session exists
    if not session_exists(session_id):
        raise HTTPException(status_code=404, detail="Session not found")
    
    # Get session name
    session_name = get_session_name(session_id, user_id)
    
    if not session_name:
        raise HTTPException(status_code=404, detail="Session not found for this user")
    
    # Get messages
    messages = get_conversation_history(session_id)
    
    # Convert to response model
    message_list = [
        Message(
            role="student" if msg["role"] == "user" else "ai",
            content=msg["content"],
            timestamp=msg["timestamp"]
        )
        for msg in messages
    ]
    
    return ConversationResponse(
        session_id=session_id,
        session_name=session_name,
        messages=message_list
    )

# ============================================
# Startup Event
# ============================================

@app.on_event("startup")
async def startup_event():
    """Test database connection on startup"""
    print("=" * 50)
    print("🚀 Starting AI Therapy Chatbot API (Gemini)")
    print("=" * 50)
    test_connection()
    
    # Test Gemini API connection
    try:
        genai.configure(api_key=os.environ.get("GEMINI_API_KEY"))
        print("✅ Gemini API configured successfully!")
    except Exception as e:
        print(f"❌ Gemini API configuration failed: {e}")
    
    print("=" * 50)

# ============================================
# Run Server
# ============================================

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)