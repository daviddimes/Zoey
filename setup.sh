#!/bin/bash

# Exit on any error
set -e

echo "🤖 Setting up Zoey Assistant..."

# Install system dependencies
echo "📦 Installing system dependencies..."
sudo apt-get update
sudo apt-get install -y \
    python3-venv \
    python3-pip \
    portaudio19-dev \
    libsndfile1 \
    libasound2-dev \
    git \
    wget \
    unzip

# Create virtual environment if it doesn't exist
if [ ! -d "env" ]; then
    echo "🐍 Creating Python virtual environment..."
    python3 -m venv env
fi

# Activate virtual environment
source env/bin/activate

# Install Python dependencies
echo "📚 Installing Python packages..."
pip install --upgrade pip
pip install -r requirements.txt

# Download Vosk model if not present
if [ ! -d "vosk-model" ]; then
    echo "🔊 Downloading Vosk model..."
    wget -nc https://alphacephei.com/vosk/models/vosk-model-small-en-us-0.15.zip
    unzip -n vosk-model-small-en-us-0.15.zip
    mv vosk-model-small-en-us-0.15 vosk-model
    rm vosk-model-small-en-us-0.15.zip
fi

# Create .env file if it doesn't exist
if [ ! -f ".env" ]; then
    echo "⚙️ Creating .env file..."
    echo "OpenAi=your-api-key-here" > .env
    echo "Please edit .env and add your OpenAI API key"
fi

# Set up audio config
echo "🎵 Configuring audio..."
# Create asound.conf if it doesn't exist
if [ ! -f "/etc/asound.conf" ]; then
    sudo tee /etc/asound.conf > /dev/null << EOL
pcm.!default {
    type asym
    playback.pcm "plughw:0,0"
    capture.pcm "plughw:0,0"
}

ctl.!default {
    type hw
    card 0
}
EOL
fi

# Create systemd service
echo "🚀 Creating systemd service..."
sudo tee /etc/systemd/system/zoey.service > /dev/null << EOL
[Unit]
Description=Zoey Voice Assistant
After=network.target sound.target

[Service]
Type=simple
User=$USER
WorkingDirectory=$PWD
Environment=PYTHONUNBUFFERED=1
ExecStart=$PWD/env/bin/python3 $PWD/zoey_pi
Restart=always
RestartSec=3

[Install]
WantedBy=multi-user.target
EOL

# Reload systemd
sudo systemctl daemon-reload

echo "✨ Setup complete! To start Zoey, run:"
echo "sudo systemctl start zoey"
echo
echo "To enable auto-start on boot:"
echo "sudo systemctl enable zoey"
echo
echo "To check status:"
echo "sudo systemctl status zoey"
echo
echo "To view logs:"
echo "journalctl -u zoey -f"