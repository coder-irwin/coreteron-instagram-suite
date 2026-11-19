# Coreteron Instagram Suite

Autonomous Instagram account registration, device verification, and session management suite powered by Playwright and real-time MXroute IMAP OTP retrieval.

---

## 5-Minute Quick Setup

### Step 1: Clone Repository
```bash
git clone https://github.com/coder-irwin/coreteron-instagram-suite.git
cd coreteron-instagram-suite
```

### Step 2: Configure Environment (.env)
Create a `.env` file in the project root directory or copy `.env.example`:
```bash
cp .env.example .env
```

If creating manually, paste the following configuration:
```env
PORT=5050
DEFAULT_EMAIL=akaash_t@meenasbeautysalon.com
DEFAULT_EMAIL_PASSWORD=MeenaBeautySalon2026!@#
DEFAULT_IMAP_SERVER=witcher.mxrouting.net
DEFAULT_IMAP_PORT=993
DEFAULT_USERNAME=meena_akaash_qa5
DEFAULT_PROXY=http://olqlayvv-rotate:a1ahaeqjq3df@p.webshare.io:80
```

### Step 3: Install Dependencies and Launch

#### Option A: 1-Click Launchers
- **macOS**: Double-click `Start_Mac.command` (or run `bash Start_Mac.command`).
- **Windows**: Double-click `Start_Windows.bat`.

#### Option B: Terminal Setup
```bash
# Create and activate virtual environment
python3 -m venv .venv
source .venv/bin/activate       # On Windows: .venv\Scripts\activate

# Install dependencies and Playwright Chromium
pip install -r requirements.txt
playwright install chromium

# Launch the application
python run_app.py
```

The Web Dashboard opens automatically at:
```
http://127.0.0.1:5050
```

---

## Capabilities & Architecture

- **Sub-Second MXroute IMAP OTP**: Automatically extracts 6-digit confirmation codes from your mailbox in under 1 second.
- **Pre-Configured Inputs**: Form fields automatically pre-populate from `.env` on page load.
- **Single & Batch Excel Mode**: Register one profile or upload `.xlsx` spreadsheets for multi-account batches.
- **Login & Device Checkpoints**: Automated login with automatic new-device email challenge handling.
- **Interactive Checkpoint Resolver**: Displays non-blocking alerts if Instagram presents visual challenges, with instant 1-click continuation.
- **Integrated Mailbox Diagnostics**: Live IMAP health check and latency tester.

---

## Project Structure

```
coreteron_instagram_suite/
|-- app.py                     # Flask web server and SSE telemetry engine
|-- run_app.py                 # Auto-browser launcher and dependency checker
|-- instagram_engine.py        # Playwright browser automation core
|-- mxroute_client.py          # Fast IMAP client for sub-second OTP extraction
|-- accounts_template.xlsx     # Spreadsheet template for batch creation
|-- templates/index.html       # Web dashboard user interface
|-- static/                    # Dashboard stylesheets and client script
|-- Start_Mac.command          # 1-Click macOS launcher script
|-- Start_Windows.bat          # 1-Click Windows launcher script
|-- requirements.txt           # Python dependencies
|-- .env.example               # Environment variables template
|-- .gitignore                 # Git ignore rules
`-- README.md                  # Operations guide
```
