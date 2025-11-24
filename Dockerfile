FROM python:3.10-slim

# Set working directory
WORKDIR /app

# Install system dependencies
RUN apt-get update && apt-get install -y \
    gcc \
    portaudio19-dev \
    && rm -rf /var/lib/apt/lists/*

# Copy requirements
COPY requirements.txt .

# Install Python dependencies
RUN pip install --no-cache-dir -r requirements.txt

# Copy application files
COPY chatbot_mysqlagent.py .
COPY streamlit_audio_recorder.py .
COPY voice_recorder.py .

# Copy Streamlit config
COPY .streamlit/ .streamlit/

# Expose port
EXPOSE 8501

# Health check
HEALTHCHECK CMD curl --fail http://localhost:8501/_stcore/health

# Run Streamlit app
CMD ["streamlit", "run", "chatbot_mysqlagent.py", "--server.port=8501", "--server.address=0.0.0.0"]
