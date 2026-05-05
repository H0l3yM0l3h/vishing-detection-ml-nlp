FROM python:3.11-slim

# Set environment variables
ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    HF_HOME=/app/.hf_cache \
    MODELS_DIR=/app/models

# Install system dependencies (ffmpeg for audio processing)
RUN apt-get update && apt-get install -y \
    ffmpeg \
    libsm6 \
    libxext6 \
    && rm -rf /var/lib/apt/lists/*

# Set working directory
WORKDIR /app

# Copy requirements and install dependencies
COPY backend/requirements.txt /app/backend/
RUN pip install --no-cache-dir --upgrade pip && \
    pip install --no-cache-dir -r /app/backend/requirements.txt

# Copy application data
# Note: In a real production environment, models and data might be downloaded 
# dynamically or mounted via volumes to keep the image small, but for HF Spaces 
# we bundle them directly.
COPY models/ /app/models/
COPY data/ /app/data/
COPY backend/ /app/backend/

# Expose port (Hugging Face Spaces requires 7860)
EXPOSE 7860

# Set the working directory to backend so relative paths work
WORKDIR /app/backend

# Command to run the FastAPI application
CMD ["uvicorn", "main:app", "--host", "0.0.0.0", "--port", "7860"]
