"""
Simple cross-platform audio recorder for voice input
Works with Windows, Mac, and Linux
"""

import sounddevice as sd
import soundfile as sf
import numpy as np
import threading
import queue
from datetime import datetime

class VoiceRecorder:
    def __init__(self, sample_rate=16000):
        """Initialize voice recorder with 16kHz sample rate (optimal for Whisper)"""
        self.sample_rate = sample_rate
        self.audio_queue = queue.Queue()
        self.recording = False
        self.audio_data = []
        
    def record_audio(self, duration=10):
        """
        Record audio from microphone for specified duration (seconds)
        
        Args:
            duration: Recording duration in seconds (default 10 seconds)
        
        Returns:
            numpy array of audio data
        """
        try:
            print(f"🎤 Recording for {duration} seconds... Speak now!")
            print("🔴 Recording started...")
            
            # Record audio
            audio = sd.rec(int(duration * self.sample_rate), 
                          samplerate=self.sample_rate, 
                          channels=1, 
                          dtype='float32')
            sd.wait()  # Wait for recording to finish
            
            print("✅ Recording completed!")
            return audio.flatten()
            
        except Exception as e:
            print(f"❌ Error recording audio: {e}")
            return None
    
    def save_audio(self, audio_data, filename=None):
        """
        Save recorded audio to file
        
        Args:
            audio_data: numpy array of audio
            filename: output filename (default: timestamp.wav)
        
        Returns:
            path to saved file
        """
        if filename is None:
            filename = f"recording_{datetime.now().strftime('%Y%m%d_%H%M%S')}.wav"
        
        try:
            sf.write(filename, audio_data, self.sample_rate)
            print(f"✅ Audio saved to {filename}")
            return filename
        except Exception as e:
            print(f"❌ Error saving audio: {e}")
            return None
    
    def audio_to_bytes(self, audio_data):
        """Convert audio numpy array to bytes for API"""
        # Convert float32 to int16
        audio_int16 = (audio_data * 32767).astype(np.int16)
        return audio_int16.tobytes()


if __name__ == "__main__":
    # Test the recorder
    recorder = VoiceRecorder()
    
    # Record for 5 seconds
    audio = recorder.record_audio(duration=5)
    
    if audio is not None:
        # Save to file
        output_file = recorder.save_audio(audio)
        
        # Convert to bytes
        audio_bytes = recorder.audio_to_bytes(audio)
        print(f"Audio bytes: {len(audio_bytes)} bytes")
