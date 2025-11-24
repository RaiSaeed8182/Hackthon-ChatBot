import streamlit as st
import sys
import os

st.set_page_config(
    page_title="MediConnect Pakistan",
    page_icon="🏥",
    layout="wide"
)

st.title("🏥 MediConnect Pakistan - AI Hospital Assistant")
st.subheader("AI-Powered Voice Assistant for Government Hospitals")

# Try to import voice module with error handling
try:
    import voice
    st.success("✅ Voice module loaded successfully!")
    voice_available = True
except ImportError as e:
    st.warning("⚠️ Voice module not available in cloud environment")
    st.info("Basic functionality available. Voice features require local setup.")
    voice_available = False

# Main functionality
st.success("🚀 Application Successfully Deployed on Streamlit Cloud!")

# Hospital Database Demo
st.write("### 🏥 Hospital Database Features")
st.write("- Patient Records Access")
st.write("- Emergency Triage System") 
st.write("- Doctor Schedules")
st.write("- Medicine Inventory")

# Voice features with fallback
if voice_available:
    if st.button("🎤 Test Voice Interface"):
        st.info("Voice features working!")
else:
    st.info("🔊 Voice interface: Available in local deployment")

# Emergency Demo
st.write("### 🚨 Emergency Triage Demo")
st.write("**Try these voice commands:**")
st.write("- 'مریض کو سانس لینے میں دشواری ہے'")
st.write("- 'سینے میں درد ہے'")
st.write("- 'بلڈ پریشر کم ہے'")

st.markdown("---")
st.write("**Live on Streamlit Sharing** | **GitHub:** https://github.com/RaiSaeed8182/Hackthon-ChatBot")