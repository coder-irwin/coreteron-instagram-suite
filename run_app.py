#!/usr/bin/env python3
"""Main Entrypoint for Coreteron Instagram Automation Suite.

1. Automatically verifies dependencies and Playwright Chromium installation.
2. Launches local Flask Web Server at http://127.0.0.1:5050.
3. Automatically opens the user's default web browser.
"""

from __future__ import annotations

import os
from pathlib import Path
import subprocess
import sys
import threading
import time
import webbrowser

BASE_DIR = Path(__file__).resolve().parent


def ensure_playwright_browsers() -> None:
    """Check if Chromium is installed; if not, install automatically."""
    print("[+] Checking Playwright Chromium browser...")
    try:
        from playwright.sync_api import sync_playwright
        with sync_playwright() as p:
            try:
                browser = p.chromium.launch(headless=True)
                browser.close()
                print("[+] Chromium browser is ready.")
                return
            except Exception:
                pass
    except Exception:
        pass

    print("[*] Installing Playwright Chromium browser (first-time setup, please wait)...")
    try:
        subprocess.run([sys.executable, "-m", "playwright", "install", "chromium"], check=True)
        print("[+] Chromium browser installed successfully.")
    except Exception as e:
        print(f"[!] Warning: Could not auto-install browser via python: {e}")


def open_browser_delayed(url: str, delay: float = 1.2) -> None:
    def _open():
        time.sleep(delay)
        print(f"[+] Opening Web Dashboard in your default browser: {url}")
        try:
            webbrowser.open(url)
        except Exception as e:
            print(f"[!] Please open {url} in your browser: {e}")

    th = threading.Thread(target=_open, daemon=True)
    th.start()


def main():
    os.chdir(str(BASE_DIR))
    ensure_playwright_browsers()

    host = "127.0.0.1"
    port = int(os.getenv("PORT", 5050))
    url = f"http://{host}:{port}"

    open_browser_delayed(url, delay=1.2)

    from app import start_server
    try:
        start_server(host=host, port=port, debug=False)
    except KeyboardInterrupt:
        print("\n[*] Coreteron Instagram Suite stopped gracefully.")


if __name__ == "__main__":
    main()

