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
from langdetect import detect, LangDetectException  # Language detection
from gtts import gTTS  # Google Text-to-Speech for multilingual support

st.set_page_config(page_title="Hospital Management", page_icon="🏥", layout="wide")

# =====================================================
# 🎨 CSS Styling
# =====================================================
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
    /* Main container with bottom padding for fixed input */
    .main-content {
        padding-bottom: 150px;
    }
    </style>
""", unsafe_allow_html=True)

# =====================================================
# 🔹 Configuration
# =====================================================
load_dotenv()

# MySQL configuration
MYSQL_CONFIG = {
    'user': os.getenv("MYSQL_USER", "root"),
    'password': os.getenv("MYSQL_PASSWORD"),
    'host': os.getenv("MYSQL_HOST", "localhost"),
    'database': os.getenv("MYSQL_DATABASE", "HospitalManagementSystem")
}

if not MYSQL_CONFIG['password']:
    st.error("❌ MYSQL_PASSWORD not found in .env file!")
    st.stop()

openai_api_key = os.getenv("OPENAI_API_KEY", "").strip()
if not openai_api_key:
    st.error("❌ OPENAI_API_KEY not found in .env file!")
    st.stop()

# =====================================================
# 🔹 Initialize OpenAI
# =====================================================
try:
    openai_client = OpenAI(api_key=openai_api_key)
    sql_llm = ChatOpenAI(
        model="gpt-3.5-turbo",
        temperature=0,
        streaming=False, 
        openai_api_key=openai_api_key
    )
except Exception as e:
    st.error(f"❌ Error initializing LLM: {e}")
    st.stop()

# =====================================================
# 🔹 Voice Functions
# =====================================================
def speech_to_text(audio_data) -> str:
    """Convert audio to text using OpenAI Whisper API."""
    try:
        if isinstance(audio_data, np.ndarray):
            wav_buffer = io.BytesIO()
            wavfile.write(wav_buffer, 16000, (audio_data * 32767).astype(np.int16))
            wav_buffer.seek(0)
            audio_bytes = wav_buffer.getvalue()
        else:
            audio_bytes = audio_data
        
        audio_file = io.BytesIO(audio_bytes)
        audio_file.name = "audio.wav"
        
        transcript = openai_client.audio.transcriptions.create(
            model="whisper-1",
            file=audio_file
        )
        return transcript.text
    except Exception as e:
        st.error(f"❌ Speech-to-Text Error: {e}")
        return ""

def text_to_speech(text: str, language_code: str = "en") -> bytes:
    """Convert text to speech using OpenAI TTS API with language-aware voice selection."""
    try:
        # Map language codes to appropriate voices
        # Using different voices for better multilingual support
        voice_map = {
            "en": "alloy",      # English
            "es": "nova",       # Spanish
            "fr": "nova",       # French
            "de": "nova",       # German
            "it": "nova",       # Italian
            "pt": "nova",       # Portuguese
            "ru": "echo",       # Russian
            "ja": "shimmer",    # Japanese
            "zh-cn": "shimmer", # Chinese (Simplified)
            "zh-tw": "shimmer", # Chinese (Traditional)
            "ko": "shimmer",    # Korean
            "hi": "echo",       # Hindi
            "ar": "echo",       # Arabic
            "tr": "nova",       # Turkish
            "pl": "echo",       # Polish
            "uk": "echo",       # Ukrainian
            "th": "shimmer",    # Thai
            "vi": "nova",       # Vietnamese
            "id": "nova",       # Indonesian
            "nl": "nova",       # Dutch
            "sv": "nova",       # Swedish
            "no": "nova",       # Norwegian
            "da": "nova",       # Danish
            "fi": "nova",       # Finnish
            "el": "echo",       # Greek
            "he": "echo",       # Hebrew
            "ur": "echo",       # Urdu
        }
        
        # Select voice based on language, default to alloy if not found
        selected_voice = voice_map.get(language_code, "alloy")
        
        response = openai_client.audio.speech.create(
            model="tts-1-hd",
            voice=selected_voice,
            input=text
        )
        return response.content
    except Exception as e:
        st.error(f"❌ Text-to-Speech Error: {e}")
        return b""

def play_audio(audio_bytes: bytes):
    """Display audio player."""
    if audio_bytes:
        st.audio(audio_bytes, format="audio/mp3")

def detect_language(text: str) -> str:
    """Detect the language of the input text."""
    try:
        lang_code = detect(text)
        return lang_code
    except LangDetectException:
        return "en"  # Default to English if detection fails

def get_language_name(lang_code: str) -> str:
    """Convert language code to language name."""
    language_map = {
        "en": "English", "es": "Spanish", "fr": "French", "de": "German",
        "it": "Italian", "pt": "Portuguese", "ru": "Russian", "ja": "Japanese",
        "zh-cn": "Chinese (Simplified)", "zh-tw": "Chinese (Traditional)",
        "ko": "Korean", "hi": "Hindi", "ar": "Arabic", "tr": "Turkish",
        "pl": "Polish", "uk": "Ukrainian", "th": "Thai", "vi": "Vietnamese",
        "id": "Indonesian", "nl": "Dutch", "sv": "Swedish", "no": "Norwegian",
        "da": "Danish", "fi": "Finnish", "el": "Greek", "he": "Hebrew", "ur": "Urdu"
    }
    return language_map.get(lang_code, lang_code.upper())

# =====================================================
# 🔹 Setup SQL Agent
# =====================================================
@st.cache_resource(ttl="2h")
def configure_mysql_db():
    try:
        connection_string = f"mysql+mysqlconnector://{MYSQL_CONFIG['user']}:{MYSQL_CONFIG['password']}@{MYSQL_CONFIG['host']}/{MYSQL_CONFIG['database']}"
        engine = create_engine(connection_string)
        db = SQLDatabase(engine)
        return db, "✅ Connected"
    except Exception as e:
        return None, f"❌ Error: {e}"

db, db_status = configure_mysql_db()
if db is None:
    sql_agent_with_history = None
else:
    try:
        toolkit = SQLDatabaseToolkit(db=db, llm=sql_llm)
        sql_agent = create_sql_agent(
            llm=sql_llm,
            toolkit=toolkit,
            verbose=True,
            agent_type=AgentType.ZERO_SHOT_REACT_DESCRIPTION,
            handle_parsing_errors=True
        )
        sql_agent_with_history = sql_agent
    except Exception as e:
        sql_agent_with_history = None

# =====================================================
# 🔹 Greeting Handler
# =====================================================
def is_greeting_or_casual(query: str) -> bool:
    query_lower = query.lower().strip()
    greetings = ['hey', 'hi', 'hello', 'good morning', 'good afternoon', 'good evening',
        'greetings', 'howdy', 'what\'s up', 'sup', 'yo', 'hii', 'heyy', 'thanks', 'thank you', 'bye', 'goodbye']
    return query_lower in greetings or len(query_lower.split()) <= 3

def get_friendly_greeting_response(query: str, language: str = "en") -> str:
    """Generate greeting response in the detected language."""
    query_lower = query.lower().strip()
    
    # Greeting responses in multiple languages
    greetings_map = {
        "en": {
            "hello": "👋 **Hello!** I can help you with hospital database queries. Try: 'Show all patients' or 'List doctors in Cardiology'",
            "thanks": "You're welcome! 😊 Anything else I can help?",
            "bye": "Goodbye! Take care! 👋",
            "default": "👋 How can I assist you today?"
        },
        "es": {
            "hello": "👋 **¡Hola!** Puedo ayudarte con consultas de la base de datos del hospital. Intenta: 'Mostrar todos los pacientes' o 'Listar médicos de Cardiología'",
            "thanks": "¡De nada! 😊 ¿Puedo ayudarte en algo más?",
            "bye": "¡Adiós! ¡Cuídate! 👋",
            "default": "👋 ¿Cómo puedo ayudarte hoy?"
        },
        "fr": {
            "hello": "👋 **Bonjour!** Je peux vous aider avec les requêtes de la base de données hospitalière. Essayez: 'Afficher tous les patients' ou 'Lister les médecins de Cardiologie'",
            "thanks": "De rien! 😊 Puis-je vous aider avec autre chose?",
            "bye": "Au revoir! Prends soin de toi! 👋",
            "default": "👋 Comment puis-je vous aider aujourd'hui?"
        },
        "de": {
            "hello": "👋 **Hallo!** Ich kann dir bei Datenbankabfragen des Krankenhauses helfen. Versuche: 'Alle Patienten anzeigen' oder 'Ärzte der Kardiologie auflisten'",
            "thanks": "Sehr gerne! 😊 Kann ich dir noch bei etwas anderem helfen?",
            "bye": "Auf Wiedersehen! Pass auf dich auf! 👋",
            "default": "👋 Wie kann ich dir heute helfen?"
        },
        "ur": {
            "hello": "👋 **السلام علیکم!** میں ہسپتال کے ڈیٹا بیس کی سوالات میں آپ کی مدد کر سکتا ہوں۔ کوشش کریں: 'تمام مریضوں کو دکھائیں' یا 'کارڈیالوجی میں ڈاکٹروں کی فہرست'",
            "thanks": "خیر مقدم! 😊 کیا میں آپ کی مزید مدد کر سکتا ہوں؟",
            "bye": "الوداع! اپنا خیال رکھو! 👋",
            "default": "👋 آج میں آپ کی کیسے مدد کر سکتا ہوں؟"
        },
        "hi": {
            "hello": "👋 **नमस्ते!** मैं अस्पताल डेटाबेस क्वेरी के साथ आपकी सहायता कर सकता हूं। कोशिश करें: 'सभी रोगियों को दिखाएं' या 'कार्डियोलॉजी में डॉक्टरों की सूची'",
            "thanks": "आपका स्वागत है! 😊 क्या मैं आपकी और मदद कर सकता हूं?",
            "bye": "अलविदा! अपना ख्याल रखो! 👋",
            "default": "👋 आज मैं आपकी कैसे मदद कर सकता हूं?"
        },
        "ar": {
            "hello": "👋 **مرحبا!** يمكنني مساعدتك في استعلامات قاعدة البيانات للمستشفى. حاول: 'عرض جميع المرضى' أو 'قائمة الأطباء في أمراض القلب'",
            "thanks": "أهلا وسهلا! 😊 هل يمكنني مساعدتك بشيء آخر؟",
            "bye": "وداعا! اعتني بنفسك! 👋",
            "default": "👋 كيف يمكنني مساعدتك اليوم؟"
        }
    }
    
    # Get the appropriate language responses (default to English if language not found)
    responses = greetings_map.get(language, greetings_map["en"])
    
    if any(word in query_lower for word in ['hey', 'hi', 'hello', 'hii', 'heyy']):
        return responses["hello"]
    elif any(word in query_lower for word in ['thanks', 'thank you']):
        return responses["thanks"]
    elif any(word in query_lower for word in ['bye', 'goodbye', 'see you']):
        return responses["bye"]
    else:
        return responses["default"]

# =====================================================
# 🔹 Sidebar
# =====================================================
st.sidebar.markdown("### 💬 Chat")
st.sidebar.info("👋 Use text or voice to ask questions!")

st.sidebar.markdown("### 🎤 Voice")
voice_enabled = st.sidebar.checkbox("🎙️ Enable Voice", value=True)

st.sidebar.markdown("### 💾 Database")
st.sidebar.markdown(f"**Status:** {db_status}\n**Host:** {MYSQL_CONFIG['host']}")

# =====================================================
# 🔹 Session Management
# =====================================================
if "store" not in st.session_state:
    st.session_state.store = {}

def get_session_history(session_id: str) -> ChatMessageHistory:
    if session_id not in st.session_state.store:
        st.session_state.store[session_id] = ChatMessageHistory()
    return st.session_state.store[session_id]

# =====================================================
# 🔹 MAIN LAYOUT
# =====================================================

# Header
st.markdown("""
    <div class="header-container">
        <h1 class="header-title">🏥 Hospital Management System</h1>
        <p class="header-subtitle">AI-Powered Database ChatBot</p>
    </div>
""", unsafe_allow_html=True)

# Session ID (hidden)
session_id = st.text_input("Session:", value="user1", key="session_id", label_visibility="collapsed")
chat_history = get_session_history(session_id)

# =====================================================
# 🔹 CHAT MESSAGES DISPLAY
# =====================================================
st.markdown("### 💬 Conversation")

if len(chat_history.messages) > 0:
    for msg in chat_history.messages:
        if isinstance(msg, HumanMessage):
            with st.chat_message("user", avatar="👤"):
                st.markdown(msg.content)
        else:
            with st.chat_message("assistant", avatar="🤖"):
                st.markdown(msg.content)
else:
    st.info("👋 Start by asking a question! You can use any language - I'll respond in the same language!")

# Add space for fixed input at bottom
st.markdown("<div style='height: 180px;'></div>", unsafe_allow_html=True)

# =====================================================
# 🔹 FIXED INPUT AT BOTTOM
# =====================================================
st.markdown("""
    <style>
    .fixed-input {
        position: fixed;
        bottom: 0;
        left: 0;
        right: 0;
        background: linear-gradient(180deg, rgba(255,255,255,0) 0%, white 30%, white 100%);
        padding: 1rem;
        z-index: 999;
        box-shadow: 0 -2px 10px rgba(0,0,0,0.1);
    }
    .input-row {
        max-width: 1200px;
        margin: 0 auto;
        background: white;
        border: 1px solid #e0e0e0;
        border-radius: 12px;
        padding: 0.75rem 1rem;
        display: flex;
        gap: 0.75rem;
        align-items: center;
        box-shadow: 0 4px 12px rgba(0,0,0,0.08);
    }
    .input-row:focus-within {
        border-color: #667eea;
        box-shadow: 0 4px 20px rgba(102, 126, 234, 0.15);
    }
    </style>
    <div class="fixed-input">
        <div class="input-row" id="input-row">
            <span id="voice-status">Ready</span>
        </div>
    </div>
""", unsafe_allow_html=True)

# Create input controls BELOW the main content but positioned fixed
col1, col2, col3, col4 = st.columns([0.5, 4, 0.5, 0.5], gap="small")

question = None
use_voice_response = False

# Voice Recording
with col1:
    if voice_enabled:
        if st.button("🎤", key="voice_btn", help="Record voice", use_container_width=True):
            st.session_state.recording = not st.session_state.get("recording", False)
            st.rerun()

# Text Input
with col2:
    if st.session_state.get("recording", False):
        st.write("🔴 **Recording... Speak now!**")
        audio_data = streamlit_live_audio_recorder()
        if audio_data is not None:
            st.session_state.audio_data = audio_data
            duration = len(audio_data) / 16000
            st.write(f"✅ Recorded: {duration:.1f}s")
            st.write("*Processing...*")
    else:
        with st.form("input_form", clear_on_submit=True):
            user_input = st.text_input("", placeholder="Ask anything...", key="text_input")
            submitted = st.form_submit_button("Send", use_container_width=True)
            if submitted and user_input:
                question = user_input
                use_voice_response = False
                st.session_state.pending_question = question
                st.session_state.pending_voice = use_voice_response

# Send Voice Button (Auto-process)
with col3:
    if st.session_state.get("audio_data") is not None:
        if st.button("📤 Send", key="send_voice", help="Send voice message", use_container_width=True):
            with st.spinner("🔄 Transcribing and processing..."):
                audio_data = st.session_state.audio_data
                # Transcribe audio to text
                question = speech_to_text(audio_data)
                st.session_state.audio_data = None
            
            if question:
                st.session_state.pending_question = question
                st.session_state.pending_voice = True
                st.rerun()
            else:
                st.error("❌ Could not understand audio. Please try again.")

# Clear History
with col4:
    if st.button("🗑️", key="clear_btn", help="Clear chat", use_container_width=True):
        chat_history.clear()
        st.session_state.pending_question = None
        st.session_state.audio_data = None
        st.rerun()

# =====================================================
# 🔹 PROCESS PENDING QUESTION
# =====================================================
if st.session_state.get("pending_question"):
    question = st.session_state.pending_question
    use_voice_response = st.session_state.get("pending_voice", False)
    
    # Clear the pending flag to avoid infinite loop
    st.session_state.pending_question = None
    st.session_state.pending_voice = False
    
    # Detect input language
    input_language = detect_language(question)
    language_name = get_language_name(input_language)
    
    # Store in session for multilingual responses
    st.session_state.input_language = input_language
    
    try:
        if is_greeting_or_casual(question):
            response_text = get_friendly_greeting_response(question, input_language)
        else:
            with st.spinner(f"🔍 Querying database... (Detected: {language_name})"):
                if sql_agent_with_history:
                    # Add language instruction to the query
                    multilingual_prompt = f"Answer in {language_name}. Question: {question}"
                    config = {"configurable": {"session_id": session_id}}
                    result = sql_agent_with_history.invoke(
                        {"input": multilingual_prompt},
                        config=config
                    )
                    response_text = result.get("output", str(result))
                else:
                    response_text = "Database not available"
        
        # Add to history with language indicator
        chat_history.add_user_message(f"[{language_name}] {question}")
        chat_history.add_ai_message(response_text)
        
        # Handle voice response - ALWAYS generate audio for voice input
        if use_voice_response:
            # Generate audio response in the detected language
            audio_response = text_to_speech(response_text[:4000], input_language)
            if audio_response:
                st.session_state.audio_response = audio_response
                st.session_state.show_audio = True
        
        # Rerun to show updated history
        st.rerun()
    
    except Exception as e:
        st.error(f"❌ Error: {e}")

# Display audio if available
if st.session_state.get("show_audio") and st.session_state.get("audio_response"):
    audio_response = st.session_state.audio_response
    st.markdown("---")
    st.markdown("### 🔉 AI Response (Audio):")
    play_audio(audio_response)
    st.session_state.show_audio = False

# Quick examples in sidebar
st.sidebar.markdown("---")
with st.sidebar.expander("💡 Examples", expanded=False):
    examples = [
        "List all patients",
        "Show doctors in Cardiology",
        "What medicines for patient P001?",
        "Show available beds",
        "List appointments today",
    ]
    for ex in examples:
        st.markdown(f"• {ex}")
