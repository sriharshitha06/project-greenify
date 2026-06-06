# Use official lightweight Python runtime
FROM python:3.12-slim

# Install system dependencies required for OpenCV and other packages
RUN apt-get update && apt-get install -y --no-install-recommends \
    libgl1-mesa-glx \
    libglib2.0-0 \
    build-essential \
    && rm -rf /var/lib/apt/lists/*

# Set working directory inside the container
WORKDIR /app

# Copy requirements file first to leverage Docker caching
COPY backend/requirements.txt ./backend/requirements.txt

# Install python dependencies
RUN pip install --no-cache-dir -r backend/requirements.txt

# Copy the entire workspace code to the container
COPY . .

# Run ML models training script to prepare model checkpoints during image build
RUN python backend/app/ml/train.py

# Expose port 8000 for FastAPI unified server
EXPOSE 8000

# Set environment variables
ENV PYTHONUNBUFFERED=1

# Command to run FastAPI server
CMD ["uvicorn", "backend.app.main:app", "--host", "0.0.0.0", "--port", "8000"]
