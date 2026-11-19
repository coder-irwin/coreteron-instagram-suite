# Coreteron Instagram Suite

Autonomous Instagram account registration, device verification, and session management suite powered by Playwright and real-time MXroute IMAP OTP retrieval.

---

## Video Demonstration

A complete product walkthrough demonstrating 1-click registration, MXroute IMAP OTP retrieval, login session verification, and batch mode is included in the repository:
- Video File: [demo/CORETERON_INSTAGRAM_SUITE_DEMO.mp4](demo/CORETERON_INSTAGRAM_SUITE_DEMO.mp4) (720p HD, 70s, 2.1 MB)

---

## 1-Click Autonomous Setup (Zero Technical Expertise)

No manual Python configuration, environment activation, or package commands are required. The automated setup script detects your operating system, configures Python, creates the isolated virtual environment, installs all dependencies and browser binaries, and opens the Web Dashboard in your default browser.

### Windows
- Double-click **`setup_and_run.bat`** (or `Start_Windows.bat`).
- If Python is not installed, the script will automatically download and install Python 3.11 with PATH enabled.

### macOS
- Double-click **`Start_Mac.command`** or open Terminal and run:
  ```bash
  ./setup_and_run.sh
  ```

### Linux (Ubuntu, Debian, Fedora, Arch)
- Open Terminal in the repository folder and run:
  ```bash
  ./setup_and_run.sh
  ```

---

## Manual Developer Setup (Optional)

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
DEFAULT_EMAIL_PASSWORD=iAaxr4oF8WaPxQ6!
DEFAULT_IMAP_SERVER=witcher.mxrouting.net
DEFAULT_IMAP_PORT=993
DEFAULT_USERNAME=meena_akaash_qa5
DEFAULT_PROXY=http://olqlayvv-rotate:a1ahaeqjq3df@p.webshare.io:80
```

### Step 3: Install Dependencies and Launch

#### Option A: 1-Click Launchers
- **macOS**: Double-click `Start_Mac.command` (or run `./setup_and_run.sh`).
- **Linux**: Run `./setup_and_run.sh`.
- **Windows**: Double-click `setup_and_run.bat`.

#### Option B: Terminal Setup by Operating System

**macOS:**
```bash
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
playwright install chromium
python run_app.py
```

**Linux (Ubuntu / Debian / RHEL):**
```bash
# On Ubuntu/Debian ensure Python venv is installed:
# sudo apt update && sudo apt install -y python3-venv python3-pip

python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
playwright install chromium
python run_app.py
```

**Windows (Command Prompt):**
```cmd
python -m venv .venv
call .venv\Scripts\activate.bat
pip install -r requirements.txt
playwright install chromium
python run_app.py
```

**Windows (PowerShell):**
```powershell
python -m venv .venv
.\.venv\Scripts\Activate.ps1
pip install -r requirements.txt
playwright install chromium
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
|-- demo/                      # Product video demonstration (MP4)
|-- templates/index.html       # Web dashboard user interface
|-- static/                    # Dashboard stylesheets and client script
|-- Start_Mac.command          # 1-Click macOS launcher script
|-- Start_Linux.sh             # 1-Click Linux launcher script
|-- Start_Windows.bat          # 1-Click Windows launcher script
|-- requirements.txt           # Python dependencies
|-- .env.example               # Environment variables template
|-- .gitignore                 # Git ignore rules
`-- README.md                  # Operations guide
```
