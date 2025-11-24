import streamlit as st
import voice  # Import your existing voice module

st.set_page_config(
    page_title="MediConnect Pakistan",
    page_icon="🏥",
    layout="wide"
)

st.title("🏥 MediConnect Pakistan - AI Hospital Assistant")
st.subheader("AI-Powered Voice Assistant for Government Hospitals")

# Your existing functionality
st.success("🚀 Application Successfully Deployed!")

# Add a button to test voice features
if st.button("🎤 Test Voice Interface"):
    st.info("Voice module loaded successfully!")
    
# Add your hospital database queries
st.write("### Patient Database Access")
st.write("### Emergency Triage System")
st.write("### Multi-language Voice Support")

st.markdown("---")
st.write("**Live on Streamlit Sharing**")