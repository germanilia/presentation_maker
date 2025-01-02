# Presentation Maker

A tool for creating presentations with a modern web-based configuration UI.

Created by Ilia German, Cloud Solution Architect at Sela and AI Group Manager.
Contact: iliag@sela.co.il

## Prerequisites

1. Python 3.8 or higher
2. Node.js 20.11.0 or higher (recommended to use nvm)
3. Visual Studio Code

## Setup

### Backend Setup

1. Create and activate Python virtual environment:
```bash
python -m venv .venv
source .venv/bin/activate  # On Windows: .venv\Scripts\activate
```

2. Install Python dependencies:
```bash
pip install -r requirements.txt
```

### Frontend Setup

1. Install nvm (Node Version Manager) if not already installed:
   - For macOS/Linux: `curl -o- https://raw.githubusercontent.com/nvm-sh/nvm/v0.39.7/install.sh | bash`
   - For Windows: Download nvm-windows from https://github.com/coreybutler/nvm-windows/releases

2. Install and use the correct Node.js version:
```bash
cd ui
nvm install    # This will read from .nvmrc
nvm use        # This will use the version specified in .nvmrc
```

3. Install Node.js dependencies:
```bash
npm install
```

## Docker Setup

1. Create a `.env` file in the project root with your environment variables:
```bash
AWS_ACCESS_KEY_ID=your_access_key
AWS_SECRET_ACCESS_KEY=your_secret_key
AWS_DEFAULT_REGION=your_region
CANVAS_MODEL=amazon.nova-canvas-v1:0
ANTHROPIC_MODEL=us.anthropic.claude-3-5-sonnet-20241022-v2:0
NOVA_MODEL=amazon.nova-lite-v1:0
SERPER_API_KEY=your_serper_api_key
YOUTUBE_API_KEY=your_youtube_api_key
```

2. Start the application using Docker Compose:
```bash
docker compose up -d
```

The web application will be available at: http://localhost:3000

### Required API Keys

- **SERPER_API_KEY**: API key for Serper.dev search service
- **YOUTUBE_API_KEY**: API key for YouTube Data API v3

You can obtain these API keys from:
- Serper API: https://serper.dev
- YouTube API: https://console.cloud.google.com/apis/library/youtube.googleapis.com

## Running the Application

### Method 1: Using VS Code (Recommended)

1. Open the project in VS Code
2. Install the recommended extensions if prompted
3. Press F5 or go to Run > Start Debugging
4. Select "Launch Frontend & Backend" from the debug configuration dropdown
5. The application will start automatically

### Method 2: Manual Start

1. Start the Flask backend:
```bash
source .venv/bin/activate  # On Windows: .venv\Scripts\activate
python src/ui_server.py
```

2. Start the React frontend (in a new terminal):
```bash
cd ui
npm start
```

3. Open your browser and navigate to http://localhost:3000

## Features

- Modern Material UI interface
- Color picker for theme customization
- Logo upload functionality
- Dynamic sub-topics management
- Real-time configuration preview
- Automatic configuration saving

## Configuration

The UI allows you to configure:
- Presentation theme colors
- Topic and sub-topics
- General instructions
- Logo
- Output path


