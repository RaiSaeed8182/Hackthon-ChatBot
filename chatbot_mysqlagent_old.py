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
from langchain_community.agent_toolkits.sql.base import create_sql_agent
from langchain_community.utilities import SQLDatabase
from langchain.agents.agent_types import AgentType
from langchain_community.agent_toolkits.sql.toolkit import SQLDatabaseToolkit
from sqlalchemy import create_engine
import sqlite3
from langchain_openai import ChatOpenAI
from openai import OpenAI

st.set_page_config(page_title="Hospital AI Assistant", page_icon="🏥")

# =====================================================
# 🎨 Beautiful UI Styling
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
    .stButton>button {
        background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
        color: white;
        border: none;
        border-radius: 8px;
        padding: 0.5rem 1.5rem;
        font-weight: 600;
    }
    </style>
""", unsafe_allow_html=True)

# Beautiful Header
st.markdown("""
    <div class="header-container">
        <h1 class="header-title">🏥 Hospital AI Assistant</h1>
        <p class="header-subtitle">Voice & Text Powered Database ChatBot</p>
    </div>
""", unsafe_allow_html=True)

# =====================================================
# 🔹 Configuration
# =====================================================
load_dotenv()

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
    llm_status = "✅ Initialized"
except Exception as e:
    llm_status = f"❌ Error: {e}"
    st.sidebar.error(f"❌ Error initializing LLM: {e}")
    st.stop()

# =====================================================
# 🔹 Voice Functions
# =====================================================
def speech_to_text(audio_file) -> str:
    """Convert audio to text using OpenAI Whisper API."""
    try:
        if audio_file is None:
            return ""

        audio_bytes = audio_file.getvalue()
        audio_buffer = io.BytesIO(audio_bytes)
        audio_buffer.name = "audio.wav"

        transcript = openai_client.audio.transcriptions.create(
            model="whisper-1",
            file=audio_buffer
        )
        return transcript.text
    except Exception as e:
        st.error(f"❌ Speech-to-Text Error: {e}")
        return ""

def text_to_speech(text: str) -> bytes:
    """Convert text to speech using OpenAI TTS API."""
    try:
        response = openai_client.audio.speech.create(
            model="tts-1-hd",
            voice="alloy",
            input=text[:4000]  # Limit length
        )
        return response.content
    except Exception as e:
        st.error(f"❌ Text-to-Speech Error: {e}")
        return b""

def play_audio(audio_bytes: bytes):
    """Display audio player."""
    if audio_bytes:
        st.audio(audio_bytes, format="audio/mp3")

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
    sql_agent = None
    agent_status = "❌ Database connection failed"
else:
    try:
        toolkit = SQLDatabaseToolkit(db=db, llm=sql_llm)
        sql_agent = create_sql_agent(
            llm=sql_llm,
            toolkit=toolkit,
            verbose=False,
            agent_type=AgentType.ZERO_SHOT_REACT_DESCRIPTION,
            handle_parsing_errors=True
        )
        agent_status = "✅ Ready"
    except Exception as e:
        agent_status = f"❌ Error: {str(e)[:50]}..."
        sql_agent = None

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
# 🔹 Create Agent with History
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
# 🔹 Sidebar
# =====================================================
st.sidebar.markdown("### 🔧 System Status")
st.sidebar.markdown(f"**🤖 LLM:** {llm_status}")
st.sidebar.markdown(f"**💾 Database:** {db_status}")
st.sidebar.markdown(f"**⚙️ SQL Agent:** {agent_status}")

st.sidebar.markdown("### 🎤 Voice Input")
voice_enabled = st.sidebar.checkbox("Enable Voice", value=True)

session_id = st.sidebar.text_input("Session ID:", value="user1")
chat_history = get_session_history(session_id)

if st.sidebar.button("🗑️ Clear Chat"):
    chat_history.clear()
    st.rerun()

# =====================================================
# 🔹 Main Chat Interface
# =====================================================
st.markdown("### 💬 Conversation")

# Show chat history
if len(chat_history.messages) > 0:
    for msg in chat_history.messages:
        if isinstance(msg, HumanMessage):
            with st.chat_message("user"):
                st.markdown(msg.content)
        else:
            with st.chat_message("assistant"):
                st.markdown(msg.content)
else:
    with st.chat_message("assistant"):
        st.markdown("👋 **Hello!** I'm your hospital database assistant. Ask me anything!")

# =====================================================
# 🔹 Input Section
# =====================================================
st.markdown("---")
st.markdown("### 💬 Ask Your Question")

# Create columns for input methods
col1, col2 = st.columns(2)

question = None
use_voice = False

# Text Input
with col1:
    st.markdown("#### 📝 Text Input")
    text_input = st.text_input("Type your question:", key="text_input")
    if text_input:
        question = text_input
        use_voice = False

# Voice Input
with col2:
    st.markdown("#### 🎤 Voice Input")
    if voice_enabled:
        audio_input = st.audio_input("Record your question:", key="audio_input")
        if audio_input is not None:
            st.audio(audio_input, format="audio/wav")
            if st.button("🎯 Transcribe & Send", use_container_width=True):
                with st.spinner("🎤 Transcribing..."):
                    transcribed = speech_to_text(audio_input)
                    if transcribed:
                        question = transcribed
                        use_voice = True
                        st.success(f"🎯 Heard: '{transcribed}'")
                    else:
                        st.error("❌ Could not understand audio")
    else:
        st.info("Voice input disabled")

# =====================================================
# 🔹 Process Question
# =====================================================
if question:
    # Display user message
    with st.chat_message("user"):
        st.write(question)

    try:
        # Check if greeting - be more specific
        greeting_words = ['hey', 'hi', 'hello', 'good morning', 'good afternoon', 'good evening', 'greetings', 'howdy', 'what\'s up', 'sup', 'yo', 'thanks', 'thank you', 'bye', 'goodbye', 'how are you', 'how do you do']
        casual_phrases = ['can you', 'could you', 'would you', 'please', 'help me', 'i need', 'tell me']

        # Only treat as greeting if it's very short OR contains only greeting words
        is_greeting = (len(question.split()) <= 3 and any(word in question.lower() for word in greeting_words)) or \
                     (question.lower().strip() in greeting_words) or \
                     (len(question.split()) <= 5 and all(word in greeting_words + casual_phrases for word in question.lower().split()) and not any(keyword in question.lower() for keyword in ['show', 'list', 'get', 'find', 'what', 'who', 'where', 'when', 'how many', 'doctor', 'patient', 'medication', 'bed', 'ward', 'appointment']))

        if is_greeting:
            # Handle greeting
            if 'hello' in question.lower() or 'hi' in question.lower():
                response = """👋 **Hello!** I'm your hospital database assistant.

I can help you query the hospital database. Try asking:
- "Show me all patients"
- "List doctors in Cardiology"
- "What medications for patient P001?"
- "Show available beds in Ward A"

Ask me anything!"""
            elif 'thanks' in question.lower():
                response = "You're welcome! 😊 How else can I help?"
            elif 'bye' in question.lower():
                response = "Goodbye! Take care! 👋"
            else:
                response = "👋 Hello! How can I help you with the hospital database?"

            with st.chat_message("assistant"):
                st.markdown(response)

            # Voice response for greetings
            if use_voice:
                with st.spinner("🔊 Generating voice response..."):
                    audio_response = text_to_speech(response)
                    if audio_response:
                        st.markdown("---")
                        st.markdown("### 🔉 Voice Response:")
                        play_audio(audio_response)

            chat_history.add_user_message(question)
            chat_history.add_ai_message(response)

        else:
            # Handle database query
            with st.chat_message("assistant"):
                message_placeholder = st.empty()

                if sql_agent_with_history is not None:
                    with st.spinner("🔍 Querying database..."):
                        try:
                            config = {"configurable": {"session_id": session_id}}
                            result = sql_agent_with_history.invoke(
                                {"input": question},
                                config=config
                            )

                            if isinstance(result, dict) and "output" in result:
                                answer = result["output"]
                            else:
                                answer = str(result)

                            # Clean up response
                            if "I don't know" in answer.lower() or "don't know" in answer.lower():
                                answer = "I'm sorry, I couldn't find that information. Try rephrasing your question or check if the data exists."
                            elif len(answer.strip()) < 10:
                                answer = "I received an incomplete response. Please try a different question."

                            message_placeholder.markdown(answer)
                            st.success("✅ Query completed!")

                            # Voice response
                            if use_voice:
                                with st.spinner("🔊 Generating voice response..."):
                                    audio_response = text_to_speech(answer[:4000])
                                    if audio_response:
                                        st.markdown("---")
                                        st.markdown("### 🔉 Voice Response:")
                                        play_audio(audio_response)

                            chat_history.add_user_message(question)
                            chat_history.add_ai_message(answer)

                        except Exception as sql_error:
                            error_msg = "I encountered an issue with your query. Please try a simpler question or check the database connection."
                            message_placeholder.error(error_msg)
                            chat_history.add_user_message(question)
                            chat_history.add_ai_message(error_msg)
                else:
                    error_msg = "❌ Database not available. Please check your connection."
                    message_placeholder.error(error_msg)
                    chat_history.add_user_message(question)
                    chat_history.add_ai_message(error_msg)

    except Exception as e:
        st.error(f"❌ Error: {str(e)[:100]}...")
        chat_history.add_user_message(question)
        chat_history.add_ai_message(f"I encountered an error: {str(e)[:100]}...")

# =====================================================
# 🔹 Examples
# =====================================================
st.sidebar.markdown("---")
with st.sidebar.expander("💡 Examples", expanded=False):
    examples = [
        "List all patients",
        "Show doctors in Cardiology",
        "What medications for patient P001?",
        "Show available beds",
        "List appointments today"
    ]
    for ex in examples:
        st.markdown(f"• {ex}")
