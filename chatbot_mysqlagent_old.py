import streamlit as st 
import os 
from dotenv import load_dotenv 
from langchain_community.chat_message_histories import ChatMessageHistory
from langchain_core.messages import HumanMessage, AIMessage
from langchain_core.runnables.history import RunnableWithMessageHistory
import time
import io
import base64
import tempfile
import numpy as np
from scipy.io import wavfile

# Import live audio recorder
from streamlit_audio_recorder import streamlit_live_audio_recorder
from langchain.agents import create_sql_agent
from langchain.sql_database import SQLDatabase
from langchain.agents.agent_types import AgentType
from langchain.agents.agent_toolkits import SQLDatabaseToolkit
from sqlalchemy import create_engine
import sqlite3
from langchain_openai import ChatOpenAI
from openai import OpenAI  # For Whisper STT and TTS

st.set_page_config(page_title="Lab Tests Assistant", page_icon="�")
#st.title("Multi-Agent ChatBot: Database + Lab Tests & Pricing")

# =====================================================
# 🎨 Beautiful UI Styling
# =====================================================
# Custom CSS for beautiful interface
st.markdown("""
    <style>
    .header-container {
        background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
        padding: 2rem;
        border-radius: 15px;
        margin-bottom: 2rem;
        box-shadow: 0 10px 30px rgba(0,0,0,0.2);
    }
    .header-title {
        color: white;
        font-size: 2.5rem;
        font-weight: bold;
        margin: 0;
        text-align: center;
    }
    .header-subtitle {
        color: rgba(255,255,255,0.9);
        font-size: 1.1rem;
        text-align: center;
        margin-top: 0.5rem;
    }
    .stButton>button {
        background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
        color: white;
        border: none;
        border-radius: 8px;
        padding: 0.5rem 1.5rem;
        font-weight: 600;
    }
    .stTextInput>div>div>input {
        border-radius: 10px;
        border: 2px solid #e0e0e0;
        padding: 0.75rem;
    }
    .stTextInput>div>div>input:focus {
        border-color: #667eea;
        box-shadow: 0 0 0 3px rgba(102, 126, 234, 0.1);
    }
    .stRadio>div {
        background: white;
        padding: 1rem;
        border-radius: 10px;
        box-shadow: 0 2px 4px rgba(0,0,0,0.1);
    }
    </style>
""", unsafe_allow_html=True)

# Beautiful Header (replaces the title)
st.markdown("""
    <div class="header-container">
        <h1 class="header-title">🏥 Hospital Management System</h1>
        <p class="header-subtitle">AI-Powered SQL Database ChatBot</p>
    </div>
""", unsafe_allow_html=True)

# =====================================================
# 🔹 Configuration
# =====================================================
load_dotenv()

# MySQL configuration - Load from .env file
MYSQL_CONFIG = {
    'user': os.getenv("MYSQL_USER", "root"),
    'password': os.getenv("MYSQL_PASSWORD"),
    'host': os.getenv("MYSQL_HOST", "localhost"),
    'database': os.getenv("MYSQL_DATABASE", "HospitalManagementSystem")
}

# Validate MySQL credentials
if not MYSQL_CONFIG['password']:
    st.error("❌ MYSQL_PASSWORD not found in .env file!")
    st.stop()

# API Keys - Load from environment
openai_api_key = os.getenv("OPENAI_API_KEY", "").strip()

if not openai_api_key:
    st.error("❌ OPENAI_API_KEY not found in .env file!")
    st.info("Please set your OpenAI API key in the .env file")
    st.stop()



# =====================================================
# 🔹 Initialize OpenAI Client & LLM
# =====================================================
try:
    # OpenAI client for Whisper (STT) and TTS
    openai_client = OpenAI(api_key=openai_api_key)
    
    # SQL Agent LLM
    sql_llm = ChatOpenAI(
        model="gpt-3.5-turbo",
        temperature=0,
        streaming=False, 
        openai_api_key=openai_api_key
    )
    llm_status = "✅ Initialized"
except Exception as e:
    llm_status = f"❌ Error: {e}"
    st.sidebar.error(f"❌ Error initializing LLM: {e}")
    st.stop()

# =====================================================
# 🔹 Voice Processing Functions (STT & TTS)
# =====================================================

def speech_to_text(audio_data) -> str:
    """Convert audio (numpy array or bytes) to text using OpenAI Whisper API."""
    try:
        # Handle both numpy arrays and bytes
        if isinstance(audio_data, np.ndarray):
            # Convert numpy array to WAV bytes using scipy
            wav_buffer = io.BytesIO()
            wavfile.write(wav_buffer, 16000, (audio_data * 32767).astype(np.int16))
            wav_buffer.seek(0)
            audio_bytes = wav_buffer.getvalue()
        else:
            audio_bytes = audio_data
        
        # Create a BytesIO object to simulate file
        audio_file = io.BytesIO(audio_bytes)
        audio_file.name = "audio.wav"
        
        # Use Whisper API
        transcript = openai_client.audio.transcriptions.create(
            model="whisper-1",
            file=audio_file
        )
        return transcript.text
    except Exception as e:
        st.error(f"❌ Speech-to-Text Error: {e}")
        return ""

def text_to_speech(text: str) -> bytes:
    """Convert text to speech using OpenAI TTS API (best quality)."""
    try:
        response = openai_client.audio.speech.create(
            model="tts-1-hd",  # Highest quality model
            voice="alloy",  # Professional voice (options: alloy, echo, fable, onyx, nova, shimmer)
            input=text
        )
        return response.content
    except Exception as e:
        st.error(f"❌ Text-to-Speech Error: {e}")
        return b""

def play_audio(audio_bytes: bytes):
    """Display audio player in Streamlit."""
    if audio_bytes:
        st.audio(audio_bytes, format="audio/mp3")

# =====================================================
# 🔹 Setup SQL Agent
# =====================================================
@st.cache_resource(ttl="2h")
def configure_mysql_db():
    """Establishes connection to the MySQL database."""
    try:
        connection_string = f"mysql+mysqlconnector://{MYSQL_CONFIG['user']}:{MYSQL_CONFIG['password']}@{MYSQL_CONFIG['host']}/{MYSQL_CONFIG['database']}"
        engine = create_engine(connection_string)
        db = SQLDatabase(engine)
        return db, "✅ Connected"
    except Exception as e:
        return None, f"❌ Error: {e}"

# Initialize database connection
db, db_status = configure_mysql_db()
if db is None:
    sql_agent = None
    agent_status = "❌ Disabled"
else:
    # Create SQL agent if database is available
    sql_agent = None
    try:
        toolkit = SQLDatabaseToolkit(db=db, llm=sql_llm)
        sql_agent = create_sql_agent(
            llm=sql_llm,
            toolkit=toolkit,
            verbose=True,
            agent_type=AgentType.ZERO_SHOT_REACT_DESCRIPTION,
            handle_parsing_errors=True
        )
        agent_status = "✅ Created"
    except Exception as e:
        agent_status = f"❌ Error: {e}"
        sql_agent = None

# =====================================================
# 🔹 Greeting Handler
# =====================================================

def is_greeting_or_casual(query: str) -> bool:
    """Check if query is a greeting or casual conversation."""
    query_lower = query.lower().strip()
    greetings = [
        'hey', 'hi', 'hello', 'good morning', 'good afternoon', 'good evening',
        'greetings', 'howdy', 'what\'s up', 'sup', 'yo', 'hii', 'heyy',
        'thanks', 'thank you', 'bye', 'goodbye', 'see you'
    ]
    return query_lower in greetings or len(query_lower.split()) <= 3

def get_friendly_greeting_response(query: str) -> str:
    """Generate a friendly greeting response."""
    query_lower = query.lower().strip()
    
    if any(word in query_lower for word in ['hey', 'hi', 'hello', 'hii', 'heyy']):
        return """👋 **Hello! Welcome to the Hospital Management System!**

I'm your AI assistant, and I can help you query the hospital database with **20 comprehensive tables**:

🏥 **Available Information:**
   - **Patients** - Patient records, demographics, status, blood types, allergies
   - **Doctors** - Doctor directory, specializations, schedules, availability
   - **Lab Results** - Test results, values, normal ranges, critical flags
   - **Medications** - Prescriptions, dosages, frequencies, status
   - **Departments** - Department info, head doctors, locations
   - **Wards** - Ward management, bed availability, charge nurses
   - **ICU Beds** - ICU bed status, equipment, patient assignments
   - **Medical Equipment** - Equipment status, maintenance, locations
   - **Pharmacy** - Medicine inventory, pricing, suppliers, expiry
   - **Disease Knowledge Base** - Disease info, symptoms, treatments, ICD10 codes
   - **Drug Information** - Drug details, uses, side effects, contraindications
   - **SOPs** - Standard operating procedures and protocols
   - **Use Case Scenarios** - Emergency scenarios and procedures
   - **Triage Symptoms** - Symptom keywords, urgency levels, actions
   - **Triage Protocols** - Triage protocols, response times, alerts
   - **Appointments** - Appointment scheduling and management
   - **Nursing Staff** - Nurse assignments, shifts, departments
   - **Surgical Procedures** - Surgery scheduling and tracking
   - **Billing** - Patient billing, payments, insurance
   - **Doctor Schedules** - Doctor schedules, OPD timings, locations

**How can I help you today?** Try asking:
- "Show me all patients"
- "List doctors in Cardiology"
- "What medications is patient P001 taking?"
- "Show available beds in Ward A"
- "List all lab results for patient P001"
- "Show appointments for today"
- "What is the status of ICU beds?"

Ask me anything about the hospital database! 😊"""
    
    elif any(word in query_lower for word in ['thanks', 'thank you']):
        return "You're welcome! 😊 Is there anything else I can help you with?"
    
    elif any(word in query_lower for word in ['bye', 'goodbye', 'see you']):
        return "Goodbye! Take care, and feel free to come back anytime you need assistance! 👋"
    
    else:
        return """👋 **Hello! I'm here to help!**

I can assist you with:
- 🏥 Hospital database queries (patients, doctors, wards, etc.)
- 🔬 Lab tests information (descriptions, pricing, normal ranges)

**What would you like to know?** Feel free to ask me anything! 😊"""

# No routing needed - we only have SQL agent now

# =====================================================
# 🔹 Session Management
# =====================================================
if "store" not in st.session_state:
    st.session_state.store = {}

def get_session_history(session_id: str) -> ChatMessageHistory:
    """Get or create chat history for a session"""
    if session_id not in st.session_state.store:
        st.session_state.store[session_id] = ChatMessageHistory()
    return st.session_state.store[session_id]

# =====================================================
# 🔹 Create Agents with History
# =====================================================
sql_agent_with_history = None

if sql_agent is not None:
    sql_agent_with_history = RunnableWithMessageHistory(
        sql_agent,
        get_session_history,
        input_messages_key="input",
        history_messages_key="chat_history"
    )

# =====================================================
# 🔹 Sidebar - All Settings and Info
# =====================================================
st.sidebar.markdown("""
    <div style='text-align: center; padding: 1rem; background: linear-gradient(135deg, #667eea 0%, #764ba2 100%); border-radius: 10px; margin-bottom: 1rem;'>
        <h2 style='color: white; margin: 0;'>🏥 System Status</h2>
    </div>
""", unsafe_allow_html=True)

# System Status
st.sidebar.markdown("### 🔧 System Status")
st.sidebar.markdown(f"""
    <div style='background: white; padding: 1rem; border-radius: 8px; margin: 0.5rem 0; box-shadow: 0 2px 4px rgba(0,0,0,0.1);'>
        <p style='margin: 0.5rem 0;'><strong>🤖 LLM:</strong> {llm_status}</p>
        <p style='margin: 0.5rem 0;'><strong>💾 Database:</strong> {db_status}</p>
        <p style='margin: 0.5rem 0;'><strong>⚙️ SQL Agent:</strong> {agent_status}</p>
    </div>
""", unsafe_allow_html=True)

# Session Settings
st.sidebar.markdown("### 👤 Session Settings")
session_id = st.sidebar.text_input(
    "Session ID:",
    value="user1",
    help="Enter a unique session ID to maintain separate chat histories",
    key="session_input"
)

# System Info
st.sidebar.markdown("### ⚙️ System Info")
st.sidebar.info("💾 **SQL Database Agent** - Query your hospital database")

# Chat Interface Info
st.sidebar.markdown("### 💬 Chat Interface")
st.sidebar.info("👋 Start a conversation! Type a message below or try saying 'hey' to get started.")

# Voice Input Options
st.sidebar.markdown("### 🎤 Voice Input")
voice_enabled = st.sidebar.checkbox("🎙️ Enable Voice Input", value=True, help="Use microphone to record messages")
# NOTE: TTS is now ONLY used when voice input is used
st.sidebar.info("📱 When using voice input, the AI will respond with voice output. Text input gets text-only responses.")


# Get chat history for current session
chat_history = get_session_history(session_id)

# Clear chat history button in sidebar
if len(chat_history.messages) > 0:
    st.sidebar.markdown("---")
    if st.sidebar.button("🗑️ Clear Chat History", use_container_width=True):
        chat_history.clear()
        st.sidebar.success("Chat history cleared!")
        st.rerun()

# =====================================================
# 🔹 Main Chat Interface - Clean Screen
# =====================================================
# Show Previous Messages
if len(chat_history.messages) > 0:
    for i, msg in enumerate(chat_history.messages):
        if isinstance(msg, HumanMessage):
            with st.chat_message("user", avatar="👤"):
                st.markdown(msg.content)
        else:
            with st.chat_message("assistant", avatar="🤖"):
                st.markdown(msg.content)

# =====================================================
# 🔹 Chat Input Section - Bottom of page
# =====================================================
st.markdown("---")

# Container for input - will be at bottom
input_container = st.container()

with input_container:
    st.markdown("### 💬 Send Your Question")
    
    # Create two columns: Text and Voice
    col_text, col_voice = st.columns([1, 1], gap="medium")
    
    question = None
    voice_input_used = False
    
    # TEXT INPUT COLUMN
    with col_text:
        st.markdown("#### 📝 Text Input")
        st.markdown("*Type your question for instant text response*")
        question = st.chat_input("💬 Ask anything about the hospital database...", key="text_input_main")
        
        if question:
            st.session_state.use_voice_response = False
            st.session_state.input_submitted = True
    
    # VOICE INPUT COLUMN
    with col_voice:
        st.markdown("#### 🎤 Voice Input")
        st.markdown("*Speak your question for voice + text response*")
        
        if voice_enabled:
            # Voice recording controls
            col_rec1, col_rec2 = st.columns([1, 1])
            with col_rec1:
                if st.button("🎙️ START RECORDING", use_container_width=True, key="voice_start"):
                    st.session_state.voice_recording = True
                    st.rerun()
            with col_rec2:
                if st.button("⏹️ STOP RECORDING", use_container_width=True, key="voice_stop"):
                    st.session_state.voice_recording = False
                    st.rerun()
            
            # Show recording status
            if st.session_state.get("voice_recording", False):
                st.info("🔴 Recording... Speak now!")
            
            # Audio recorder (works in background)
            audio_data = streamlit_live_audio_recorder()
            
            if audio_data is not None and not st.session_state.get("voice_recording", False):
                # Show recording info
                duration = len(audio_data) / 16000
                st.success(f"✅ Recorded: {duration:.2f}s")
                
                # Transcribe button
                if st.button("📤 Transcribe & Send", use_container_width=True, key="transcribe_voice"):
                    with st.spinner("🔄 Transcribing..."):
                        transcribed_text = speech_to_text(audio_data)
                    
                    if transcribed_text:
                        st.session_state.voice_question = transcribed_text
                        st.session_state.use_voice_response = True
                        st.success("✅ Sending to AI with voice response enabled...")
                        st.session_state.recorded_audio = None
                        st.rerun()
                    else:
                        st.error("❌ Could not transcribe audio. Please try again.")
            
            st.markdown("---")
            st.markdown("**Or type your question below:**")
            voice_text = st.text_area("📝 Type your question:", height=100, key="voice_text_fallback")
            if voice_text:
                if st.button("📤 Send (with Voice Response)", use_container_width=True, key="send_text_question"):
                    st.session_state.voice_question = voice_text
                    st.session_state.use_voice_response = True
                    st.success("✅ Sending with voice response enabled...")
                    st.rerun()
        else:
            st.info("🎙️ Voice input is disabled. Enable it in the sidebar to use this feature.")

# Check if there's a voice question stored
use_voice_response = st.session_state.get("use_voice_response", False)
if "voice_question" in st.session_state and st.session_state.voice_question:
    question = st.session_state.voice_question
    st.session_state.voice_question = None  # Clear it after use
    st.session_state.use_voice_response = False  # Reset flag

if question:
    # Display user message
    with st.chat_message("user"):
        st.write(question)
    
    try:
        # Check if it's a greeting first
        if is_greeting_or_casual(question):
            # Handle greetings with friendly response
            with st.chat_message("assistant"):
                friendly_response = get_friendly_greeting_response(question)
                st.markdown(friendly_response)
            
            # Add to chat history
            chat_history.add_user_message(question)
            chat_history.add_ai_message(friendly_response)
            
            # Convert to speech ONLY if voice input was used
            if use_voice_response:
                with st.spinner("🔊 Generating voice response..."):
                    audio_response = text_to_speech(friendly_response)
                    if audio_response:
                        st.markdown("---")
                        st.markdown("### 🔉 Voice Response:")
                        play_audio(audio_response)
        else:
            # Use SQL agent directly
            config = {"configurable": {"session_id": session_id}}
            
            # Display assistant message
            with st.chat_message("assistant"):
                message_placeholder = st.empty()
                full_response = ""
                
                if sql_agent_with_history is not None:
                    with st.spinner("🔍 Querying database..."):
                        try:
                            response = sql_agent_with_history.invoke(
                                {"input": question},
                                config=config
                            )
                            answer = response["output"] if "output" in response else str(response)
                            full_response = answer
                            message_placeholder.write(full_response)
                        except Exception as sql_error:
                            st.error(f"SQL Agent Error: {sql_error}")
                            full_response = f"I encountered an error while querying the database: {str(sql_error)}. Please try rephrasing your question or check the database connection."
                            message_placeholder.write(full_response)
                else:
                    full_response = "Sorry, the SQL agent is not available. Please check your database connection and configuration."
                    message_placeholder.write(full_response)
                
                # Convert to speech ONLY if voice input was used
                if use_voice_response and full_response:
                    st.markdown("---")
                    with st.spinner("🔊 Generating voice response..."):
                        # Limit response length for TTS (API has 4096 char limit)
                        tts_text = full_response[:4000] if len(full_response) > 4000 else full_response
                        audio_response = text_to_speech(tts_text)
                        if audio_response:
                            st.markdown("### 🔉 Voice Response:")
                            play_audio(audio_response)
                
                # Add messages to history
                chat_history.add_user_message(question)
                chat_history.add_ai_message(full_response)
        
    except Exception as e:
        st.error(f"❌ Unexpected Error: {e}")
        import traceback
        st.code(traceback.format_exc())
        
        # Fallback response
        fallback_response = "I encountered an unexpected error. Please try rephrasing your question or check your configuration. If the problem persists, please contact support."
        with st.chat_message("assistant"):
            st.write(fallback_response)
        chat_history.add_user_message(question)
        chat_history.add_ai_message(fallback_response)

# Database Info
st.sidebar.markdown("### 💾 Database Info")
st.sidebar.markdown(f"""
    <div style='background: white; padding: 1rem; border-radius: 8px; margin: 0.5rem 0; box-shadow: 0 2px 4px rgba(0,0,0,0.1);'>
        <p style='margin: 0.5rem 0;'><strong>🌐 Host:</strong> {MYSQL_CONFIG['host']}</p>
        <p style='margin: 0.5rem 0;'><strong>📊 Database:</strong> {MYSQL_CONFIG['database']}</p>
    </div>
""", unsafe_allow_html=True)

# Session Info
st.sidebar.markdown("### 📝 Session Info")
st.sidebar.markdown(f"""
    <div style='background: white; padding: 1rem; border-radius: 8px; margin: 0.5rem 0; box-shadow: 0 2px 4px rgba(0,0,0,0.1);'>
        <p style='margin: 0.5rem 0;'><strong>👤 Session:</strong> {session_id}</p>
        <p style='margin: 0.5rem 0;'><strong>💬 Messages:</strong> {len(chat_history.messages)}</p>
    </div>
""", unsafe_allow_html=True)

# Show available sessions
if len(st.session_state.store) > 1:
    st.sidebar.markdown("### 📚 Other Sessions")
    for sid in st.session_state.store.keys():
        if sid != session_id:
            message_count = len(st.session_state.store[sid].messages)
            st.sidebar.markdown(f"📝 **{sid}** ({message_count} messages)")

# =====================================================
# 🔹 Usage Examples - Beautiful Cards
# =====================================================
st.sidebar.markdown("---")
st.sidebar.markdown("### 💡 Quick Examples")

with st.sidebar.expander("🏥 Database Queries", expanded=False):
    examples_db = [
        "List all patients",
        "Show patients in ICU",
        "Which doctors are in Cardiology?",
        "What medications is patient P001 taking?",
        "Show available beds in Ward A",
        "List all lab results for patient P001",
        "What equipment is in maintenance?",
        "Show pharmacy stock levels",
        "Show appointments for today",
        "List all nurses in Ward A",
        "Show surgical procedures scheduled",
        "Display billing information for patient P001",
        "Show doctor schedules for Monday",
        "List triage symptoms with high urgency",
        "Show disease knowledge for diabetes"
    ]
    for ex in examples_db:
        st.markdown(f"• `{ex}`")
