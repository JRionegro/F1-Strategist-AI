#!/bin/bash
# F1 Strategist AI - Unix/Linux/macOS Launcher
# ============================================

echo ""
echo "========================================"
echo "  F1 STRATEGIST AI - DASH APPLICATION"
echo "========================================"
echo ""

# Check if virtual environment exists
if [ ! -d "venv" ]; then
    echo "ERROR: Virtual environment not found!"
    echo "Please run: python3 -m venv venv"
    exit 1
fi

# Activate virtual environment
echo "Activating virtual environment..."
source venv/bin/activate

# Check if app_dash.py exists
if [ ! -f "app_dash.py" ]; then
    echo "ERROR: app_dash.py not found!"
    echo "Please ensure you're in the project root directory."
    exit 1
fi

# Check if .env file exists
if [ ! -f ".env" ]; then
    echo "WARNING: .env file not found!"
    echo "Creating .env template..."
    cat > .env << 'EOF'
# LLM API Keys (at least one required)
GEMINI_API_KEY=your_gemini_api_key_here
ANTHROPIC_API_KEY=your_claude_api_key_here

# Logging Configuration
LOG_LEVEL_F1_DATA=DEBUG
LOG_LEVEL_F1_CHAT=DEBUG
LOG_LEVEL_F1_TRACK_MAP=DEBUG
EOF
    echo "Please edit .env with your API keys before running."
    exit 1
fi

# Display configuration
echo "Python version: $(python --version)"
echo "Working directory: $(pwd)"
echo ""

# Run the application
echo "Starting F1 Strategist AI..."
echo "========================================"
echo ""
python app_dash.py
