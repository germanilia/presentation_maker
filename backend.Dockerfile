# Use Python 3.11 as base image
FROM python:3.11-slim

# Set working directory
WORKDIR /app

# Install system dependencies
RUN apt-get update && apt-get install -y \
    gcc \
    python3-dev \
    && rm -rf /var/lib/apt/lists/*

# Copy requirements file
COPY requirements.txt .

# Install Python dependencies
RUN pip install -r requirements.txt

# Ensure uvicorn is explicitly installed
RUN pip install uvicorn

# Copy backend code (excluding output directory)
COPY . .
RUN rm -rf output && mkdir output

# Set environment variables
ENV AWS_ACCESS_KEY_ID=""
ENV AWS_SECRET_ACCESS_KEY=""
ENV SERPER_API_KEY=""
ENV YOUTUBE_API_KEY=""
ENV AWS_DEFAULT_REGION="us-east-1"
ENV CANVAS_MODEL="amazon.nova-canvas-v1:0"
ENV ANTHROPIC_MODEL="us.anthropic.claude-3-5-sonnet-20241022-v2:0"
ENV NOVA_MODEL="amazon.nova-lite-v1:0"

EXPOSE 9090

# Use uvicorn to start the server
CMD ["python", "src/ui_server.py"] 