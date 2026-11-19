# Coreteron Instagram Suite — Operations Guide

> **Enterprise Operations Manual**  
> *1-Click Autonomous Setup & Management*

---

## Table of Contents
1. [Overview & Capabilities](#1-overview--capabilities)
2. [Prerequisites](#2-prerequisites)
3. [1-Click Setup & Launching](#3-1-click-setup--launching)
   - [On Apple Mac (macOS)](#on-apple-mac-macos)
   - [On Windows PC](#on-windows-pc)
4. [Step-by-Step: Account Registration](#4-step-by-step-account-registration)
5. [Interactive Verification Checkpoints](#5-interactive-verification-checkpoints)
6. [Step-by-Step: Account Login & Session Verification](#6-step-by-step-account-login--session-verification)
7. [Mailbox Diagnostics](#7-mailbox-diagnostics)
8. [Frequently Asked Questions & Troubleshooting](#8-frequently-asked-questions--troubleshooting)
9. [Quick Reference Cheat Sheet](#9-quick-reference-cheat-sheet)

---

## 1. Overview & Capabilities

The **Coreteron Instagram Suite** is a desktop application engineered for high-reliability Instagram registration, login verification, and session management.

### Key Capabilities:
- **Instant Mailbox OTP Retrieval**: Connects directly to MXroute mail servers (`witcher.mxrouting.net`) to extract Instagram verification codes in under 1 second.
- **Automated Interaction Handling**: Automatically handles consent dialogs, "Save login info", "Turn on notifications", and modal confirmations.
- **Autonomous Code Refresh**: If Instagram marks an OTP as expired, the system triggers code regeneration, reads the new code from the mailbox, and retries.
- **Human-in-the-Loop Safeguard**: If Instagram presents visual challenges (CAPTCHA) or SMS prompts, the application pauses and alerts you to complete it in the visible browser window, then resumes execution.
- **Active Session Verification**: Automatically navigates to the home feed and performs scrolls to verify session authentication.

---

## 2. Prerequisites

Runtime Requirement:
- **Python 3**: Verify via `python3 --version` or `python --version`.
- Official download: [python.org/downloads](https://www.python.org/downloads/).
  - For Windows: Check "Add python.exe to PATH" during installation.

---

## 3. 1-Click Setup & Launching

### On Apple Mac (macOS)
1. Navigate to the `coreteron_instagram_suite` folder.
2. Double-click `Start_Mac.command` (or execute `bash Start_Mac.command` in Terminal).
3. The launcher automatically:
   - Verifies Python runtime
   - Installs required dependencies
   - Verifies Playwright Chromium browser
   - Launches the web dashboard at: `http://127.0.0.1:5050`

Note for macOS: If gatekeeper prompts that the script was downloaded from the internet, right-click `Start_Mac.command` and select **Open**.

---

### On Windows PC
1. Navigate to the `coreteron_instagram_suite` folder.
2. Double-click `Start_Windows.bat`.
3. The launcher configures the environment and launches your default browser to: `http://127.0.0.1:5050`.

---

## 4. Step-by-Step: Account Registration

1. Open the **1-Click Registration** tab in the dashboard.
2. Form fields are pre-populated from your `.env` configuration.
3. Review or adjust values:
   - **Email Address**: `akaash_t@meenasbeautysalon.com`
   - **Email Password**: Mailbox IMAP password
   - **Instagram Username**: Target account handle
   - **Instagram Password**: Account password
   - *(Optional)* Click **Randomize Profile** to generate randomized handle and identity details.
4. Click **Start Automated Registration**:
   - The browser window opens.
   - Credentials and birthday are entered.
   - MXroute IMAP extracts the 6-digit confirmation code in under 1 second.
   - After confirmation, the session navigates to the home feed to verify active status.
   - The dashboard displays a confirmed Success status.

---

## 5. Interactive Verification Checkpoints

If Instagram displays a visual check or phone verification prompt:

1. **Dashboard Alert**:
   An amber banner appears:
   > Action Required: Human Verification in Browser
2. **Action**:
   Complete the challenge in the visible browser window.
3. **Resume Automation**:
   Click **I Solved It - Resume Automation** on the dashboard. The bot will also automatically detect challenge completion within 3 seconds and resume.

---

## 6. Step-by-Step: Account Login & Session Verification

Use this mode to authenticate existing accounts and confirm session validity:

1. Navigate to the **Account Login** tab.
2. Enter the **Instagram Username** and **Instagram Password**.
3. *(Optional)* Provide the **Mailbox Password**: If Instagram requests a device verification code, the bot reads and submits it automatically via IMAP.
4. Click **Login & Verify Session**.
5. The bot signs in, dismisses popups, scrolls the feed, and validates the session.

---

## 7. Mailbox Diagnostics

Test your mailbox connection prior to running campaigns:

1. Navigate to the **Test Mailbox** tab.
2. Enter your Email Address and Password.
3. Click **Test IMAP Connection**.
4. Status feedback:
   - **Success**: Verified connection to `witcher.mxrouting.net:993` with mailbox latency.
   - **Failed**: Displays error diagnostic (e.g. invalid password or network timeout).

---

## 8. Frequently Asked Questions & Troubleshooting

### Q1: The launcher reports "Python is not detected"?
Install Python 3 from [python.org/downloads](https://www.python.org/downloads/). On Windows, ensure "Add python.exe to PATH" is enabled.

### Q2: Instagram displays "This code doesn't work. Check the code and try again"?
The engine handles this automatically: it requests a replacement code, retrieves the fresh code from IMAP, and enters it without manual intervention.

### Q3: How to stop the server?
Close the browser tab and press `Ctrl + C` in the Terminal or Command Prompt window.

### Q4: What is the default email server?
- IMAP Server: `witcher.mxrouting.net`
- Port: `993` (SSL encrypted)

---

## 9. Quick Reference Cheat Sheet

| Action | Command / Procedure |
| :--- | :--- |
| **Start on macOS** | Double-click `Start_Mac.command` |
| **Start on Windows** | Double-click `Start_Windows.bat` |
| **Dashboard URL** | `http://127.0.0.1:5050` |
| **Verify Mailbox** | Navigate to "Test Mailbox" tab -> Click "Test IMAP Connection" |
| **Generate Credentials** | Click "Randomize Profile" button on Registration tab |
| **Solve Challenge** | Complete challenge in browser -> Click "I Solved It - Resume" |
