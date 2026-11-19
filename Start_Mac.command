#!/bin/bash
# ==============================================================================
# Coreteron Instagram Suite - 1-Click macOS Launcher
# Double-click this file to start the application. Zero Git required!
# ==============================================================================

# Move to script directory
DIR="$( cd "$( dirname "${BASH_SOURCE[0]}" )" && pwd )"
cd "$DIR"

echo "=================================================================="
echo "    [+] STARTING CORETERON INSTAGRAM SUITE (macOS)                "
echo "=================================================================="

# Check for Python 3
if ! command -v python3 &> /dev/null; then
    echo ""
    echo "[-] Python 3 is not detected on your system."
    echo "[!] Please download and install Python from: https://www.python.org/downloads/"
    echo "    or run 'xcode-select --install' in Terminal."
    echo ""
    read -p "Press Enter to exit..."
    exit 1
fi

echo "[+] Python detected: $(python3 --version)"

# Create virtual environment if it doesn't exist
if [ ! -d ".venv" ]; then
    echo "[+] Initializing isolated environment (.venv)..."
    python3 -m venv .venv
fi

# Activate virtual environment
source .venv/bin/activate

# Install / update dependencies quietly
echo "[+] Verifying package dependencies..."
python -m pip install -q --upgrade pip
python -m pip install -q -r requirements.txt

# Ensure Playwright browser is ready
echo "[+] Verifying Playwright browser..."
python -m playwright install chromium

echo "=================================================================="
echo "[+] Starting Web Dashboard & Opening Browser..."
echo "=================================================================="

# Launch the app
python run_app.py

