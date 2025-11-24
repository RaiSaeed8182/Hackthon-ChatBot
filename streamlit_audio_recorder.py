"""
Streamlit integration for live audio recording using sounddevice
Captures audio directly from microphone in real-time
"""

import streamlit as st
import sounddevice as sd
import numpy as np
import threading
from queue import Queue
import time


class StreamlitAudioRecorder:
    """Live audio recorder for Streamlit apps"""
    
    def __init__(self, sample_rate=16000, channels=1):
        self.sample_rate = sample_rate
        self.channels = channels
        self.audio_data = []
        self.recording = False
        self.stream = None
        
    def audio_callback(self, indata, frames, time_info, status):
        """Callback function for audio stream"""
        if status:
            st.warning(f"Audio status: {status}")
        self.audio_data.append(indata.copy())
    
    def start_recording(self):
        """Start recording audio from microphone"""
        try:
            self.audio_data = []
            self.recording = True
            
            # Create audio stream
            self.stream = sd.InputStream(
                channels=self.channels,
                samplerate=self.sample_rate,
                callback=self.audio_callback,
                blocksize=8192
            )
            
            self.stream.start()
            return True
        except Exception as e:
            st.error(f"❌ Error starting recording: {e}")
            return False
    
    def stop_recording(self):
        """Stop recording and return audio data"""
        try:
            if self.stream:
                self.stream.stop()
                self.stream.close()
            
            self.recording = False
            
            # Combine all audio chunks
            if self.audio_data:
                audio = np.concatenate(self.audio_data, axis=0)
                return audio.flatten()
            return None
            
        except Exception as e:
            st.error(f"❌ Error stopping recording: {e}")
            return None


def streamlit_live_audio_recorder():
    """
    Streamlit component for live audio recording
    Returns the recorded audio as numpy array or None
    """
    
    # Initialize session state
    if "recorder" not in st.session_state:
        st.session_state.recorder = StreamlitAudioRecorder()
    
    if "is_recording" not in st.session_state:
        st.session_state.is_recording = False
    
    if "recorded_audio" not in st.session_state:
        st.session_state.recorded_audio = None
    
    if "recording_time" not in st.session_state:
        st.session_state.recording_time = 0
    
    recorder = st.session_state.recorder
    
    # Create columns for buttons
    col1, col2, col3 = st.columns([1, 1, 2])
    
    with col1:
        if st.button("🎙️ START RECORDING", use_container_width=True, key="start_rec"):
            if not st.session_state.is_recording:
                st.session_state.is_recording = True
                recorder.start_recording()
                st.session_state.start_time = time.time()
                st.success("🔴 Recording started! Speak now...")
                st.rerun()
    
    with col2:
        if st.button("⏹️ STOP RECORDING", use_container_width=True, key="stop_rec"):
            if st.session_state.is_recording:
                st.session_state.is_recording = False
                audio_data = recorder.stop_recording()
                st.session_state.recorded_audio = audio_data
                st.success("✅ Recording stopped! Processing...")
                st.rerun()
    
    # Show recording status
    if st.session_state.is_recording:
        elapsed = time.time() - st.session_state.start_time
        st.info(f"⏱️ Recording... {elapsed:.1f}s")
        st.markdown("---")
        # Auto-refresh to show timer
        import time as time_module
        time_module.sleep(0.5)
        st.rerun()
    
    # Return recorded audio
    if st.session_state.recorded_audio is not None:
        return st.session_state.recorded_audio
    
    return None


if __name__ == "__main__":
    st.title("🎤 Live Audio Recorder Test")
    
    audio = streamlit_live_audio_recorder()
    
    if audio is not None:
        st.success(f"✅ Audio recorded: {len(audio)} samples")
        st.write(f"Duration: {len(audio) / 16000:.2f} seconds")
