#!/usr/bin/env python3
"""Flask Web Application for Coreteron Instagram Automation Suite.

Provides an intuitive, 1-click web interface for:
- 1-Click Instagram account registration with MXroute IMAP OTP
- Instagram login & device verification
- Batch Excel registration mode
- Live Mailbox connection tester
- Real-time Server-Sent Events (SSE) progress streaming
"""

from __future__ import annotations

import asyncio
from datetime import datetime
import json
import logging
import os
from pathlib import Path
import queue
import random
import re
import threading
import time
from typing import Any, Dict, List, Optional

from flask import Flask, Response, jsonify, render_template, request, send_file
import pandas as pd

from instagram_engine import (
    AccountData,
    AutomationSession,
    DEFAULT_BIRTHDAY,
    generate_random_credentials,
)
from mxroute_client import DEFAULT_SERVER as MXROUTE_DEFAULT_SERVER, MXRouteIMAPReader
from smspool_client import SMSPoolClient, DEFAULT_COUNTRY as SMSPOOL_DEFAULT_COUNTRY, DEFAULT_SERVICE as SMSPOOL_DEFAULT_SERVICE

BASE_DIR = Path(__file__).resolve().parent
STATIC_DIR = BASE_DIR / "static"
TEMPLATES_DIR = BASE_DIR / "templates"
TEMPLATE_EXCEL = BASE_DIR / "accounts_template.xlsx"

# Load .env configuration
env_path = BASE_DIR / ".env"
if env_path.exists():
    try:
        with open(env_path, "r", encoding="utf-8") as f:
            for line in f:
                line = line.strip()
                if line and not line.startswith("#") and "=" in line:
                    k, v = line.split("=", 1)
                    os.environ.setdefault(k.strip(), v.strip().strip('"').strip("'"))
    except Exception:
        pass

app = Flask(__name__, template_folder=str(TEMPLATES_DIR), static_folder=str(STATIC_DIR))
app.config["SECRET_KEY"] = "coreteron_secure_secret_2026"
app.config["MAX_CONTENT_LENGTH"] = 16 * 1024 * 1024

# Global State for Real-Time Streaming & Control
event_queue: queue.Queue = queue.Queue(maxsize=1000)
human_signal_event = threading.Event()
active_task_lock = threading.Lock()
is_task_running = False
current_task_info: Dict[str, Any] = {"status": "idle", "task": None, "start_time": None}


def publish_event(event_dict: Dict[str, Any]) -> None:
    """Push event to SSE queue for real-time frontend streaming."""
    try:
        event_queue.put_nowait(event_dict)
    except queue.Full:
        pass


def run_async_task(coro) -> Any:
    """Helper to run asyncio coroutine in dedicated background thread."""
    loop = asyncio.new_event_loop()
    asyncio.set_event_loop(loop)
    try:
        return loop.run_until_complete(coro)
    finally:
        loop.close()


# ---------------------------------------------------------------------------
# Web Routes
# ---------------------------------------------------------------------------

@app.route("/")
def index():
    return render_template(
        "index.html",
        default_email=os.getenv("DEFAULT_EMAIL", "akaash_t@meenasbeautysalon.com"),
        default_email_password=os.getenv("DEFAULT_EMAIL_PASSWORD", "iAaxr4oF8WaPxQ6!"),
        default_proxy=os.getenv("DEFAULT_PROXY", "http://olqlayvv-rotate:a1ahaeqjq3df@p.webshare.io:80"),
        default_imap_server=os.getenv("DEFAULT_IMAP_SERVER", MXROUTE_DEFAULT_SERVER),
        default_imap_port=os.getenv("DEFAULT_IMAP_PORT", "993"),
        default_username=os.getenv("DEFAULT_USERNAME") or f"meena_akaash_qa{random.randint(100, 9999)}",
        default_smspool_key=os.getenv("SMSPOOL_API_KEY", ""),
    )


@app.route("/api/system-status")
def system_status():
    """Return health check and environment status."""
    return jsonify({
        "status": "online",
        "timestamp": datetime.now().isoformat(),
        "is_task_running": is_task_running,
        "current_task": current_task_info,
        "default_imap_server": MXROUTE_DEFAULT_SERVER,
        "default_imap_port": 993,
    })


@app.route("/api/generate-credentials")
def api_generate_credentials():
    """Return randomized credentials for 1-click registration."""
    creds = generate_random_credentials(prefix="coreteron")
    return jsonify({"success": True, "data": creds})


@app.route("/api/test-mailbox", methods=["POST"])
def api_test_mailbox():
    """Test IMAP credentials before running automation."""
    payload = request.get_json(force=True, silent=True) or {}
    email = payload.get("email", "").strip()
    password = payload.get("password", "").strip()
    server = payload.get("server", MXROUTE_DEFAULT_SERVER).strip()
    try:
        port = int(payload.get("port", 993))
    except Exception:
        port = 993

    if not email or not password:
        return jsonify({"success": False, "message": "Email and password are required."}), 400

    start_t = time.time()
    reader = MXRouteIMAPReader(email_address=email, password=password, server=server, port=port)
    try:
        reader.connect()
        msg_cnt = reader.get_message_count()
        reader.disconnect()
        elapsed = round(time.time() - start_t, 2)
        return jsonify({
            "success": True,
            "message": f"Successfully connected to {server}:{port}! Inbox contains {msg_cnt} messages. Latency: {elapsed}s.",
            "message_count": msg_cnt,
            "latency": elapsed,
        })
    except Exception as e:
        return jsonify({
            "success": False,
            "message": f"Connection failed to {server}:{port}: {str(e)}",
        }), 400


@app.route("/api/register", methods=["POST"])
def api_register():
    global is_task_running, current_task_info
    if is_task_running:
        return jsonify({"success": False, "message": "Another automation task is already running. Please wait for it to complete."}), 409

    data = request.get_json(force=True, silent=True) or {}
    email = data.get("email", "").strip()
    email_password = data.get("email_password", "").strip()
    username = data.get("username", "").strip()
    full_name = data.get("full_name", "").strip()
    password = data.get("password", "").strip()
    birthday = data.get("birthday", DEFAULT_BIRTHDAY).strip()
    imap_server = data.get("imap_server", MXROUTE_DEFAULT_SERVER).strip()
    try:
        imap_port = int(data.get("imap_port", 993))
    except Exception:
        imap_port = 993

    headless = bool(data.get("headless", False))
    proxy = str(data.get("proxy", "")).strip()

    if not email or not email_password or not username or not password:
        return jsonify({"success": False, "message": "Email, Email Password, Username, and Password are all required."}), 400

    account = AccountData(
        email=email,
        password=password,
        username=username,
        full_name=full_name or "Coreteron User",
        email_password=email_password,
        imap_server=imap_server,
        imap_port=imap_port,
        birthday=birthday or DEFAULT_BIRTHDAY,
        proxy=proxy,
        smspool_api_key=data.get("smspool_api_key") or os.getenv("SMSPOOL_API_KEY", ""),
        smspool_country=data.get("smspool_country", "US"),
    )

    def background_runner():
        global is_task_running, current_task_info
        with active_task_lock:
            is_task_running = True
            current_task_info = {
                "status": "running",
                "task": "registration",
                "target": email,
                "start_time": datetime.now().isoformat(),
            }

        session = AutomationSession(
            base_dir=BASE_DIR,
            callback=publish_event,
            human_signal=human_signal_event,
        )

        try:
            res = run_async_task(
                session.register_account(account, headless=headless)
            )
            publish_event({
                "timestamp": datetime.now().strftime("%H:%M:%S"),
                "step": "completed",
                "title": "Task Finished",
                "message": res.get("details", "Finished"),
                "level": "success" if res.get("success") else "error",
                "human_required": False,
                "data": res,
            })
        except Exception as e:
            publish_event({
                "timestamp": datetime.now().strftime("%H:%M:%S"),
                "step": "exception",
                "title": "Task Crashed",
                "message": str(e),
                "level": "error",
                "human_required": False,
                "data": {},
            })
        finally:
            with active_task_lock:
                is_task_running = False
                current_task_info = {"status": "idle", "task": None, "start_time": None}

    th = threading.Thread(target=background_runner, daemon=True)
    th.start()

    return jsonify({"success": True, "message": "Registration task initiated in background."})


@app.route("/api/batch-register", methods=["POST"])
def api_batch_register():
    global is_task_running, current_task_info
    if is_task_running:
        return jsonify({"success": False, "message": "Another automation task is already running. Please wait for it to complete."}), 409

    if "file" not in request.files:
        return jsonify({"success": False, "message": "No Excel file uploaded."}), 400

    file = request.files["file"]
    if not file.filename.endswith((".xlsx", ".xls")):
        return jsonify({"success": False, "message": "Please upload a valid Excel file (.xlsx or .xls)."}), 400

    try:
        df = pd.read_excel(file)
    except Exception as e:
        return jsonify({"success": False, "message": f"Could not read Excel file: {str(e)}"}), 400

    required_cols = ["email", "password", "username", "email_password"]
    missing = [c for c in required_cols if c not in df.columns]
    if missing:
        return jsonify({
            "success": False,
            "message": f"Missing required columns in Excel: {', '.join(missing)}. Required: email, password, username, email_password",
        }), 400

    accounts_to_run: List[AccountData] = []
    for _, row in df.iterrows():
        em = str(row.get("email", "")).strip()
        em_pwd = str(row.get("email_password", "")).strip()
        usr = str(row.get("username", "")).strip()
        pwd = str(row.get("password", "")).strip()
        fn = str(row.get("full_name", "")).strip() or "Coreteron User"
        bday = str(row.get("birthday", "")).strip() or DEFAULT_BIRTHDAY
        prx = str(row.get("proxy", "")).strip()
        if prx.lower() == "nan":
            prx = ""

        if em and em_pwd and usr and pwd and em.lower() != "nan" and usr.lower() != "nan":
            accounts_to_run.append(AccountData(
                email=em,
                email_password=em_pwd,
                username=usr,
                password=pwd,
                full_name=fn,
                birthday=bday if bday.lower() != "nan" else DEFAULT_BIRTHDAY,
                proxy=prx,
            ))

    if not accounts_to_run:
        return jsonify({"success": False, "message": "No valid account rows found in the uploaded file."}), 400

    def batch_runner():
        global is_task_running, current_task_info
        with active_task_lock:
            is_task_running = True
            current_task_info = {
                "status": "running",
                "task": "batch_registration",
                "total": len(accounts_to_run),
                "start_time": datetime.now().isoformat(),
            }

        session = AutomationSession(
            base_dir=BASE_DIR,
            callback=publish_event,
            human_signal=human_signal_event,
        )

        publish_event({
            "timestamp": datetime.now().strftime("%H:%M:%S"),
            "step": "batch_start",
            "title": "Batch Started",
            "message": f"Loaded {len(accounts_to_run)} accounts from Excel. Starting sequential registration...",
            "level": "info",
            "human_required": False,
        })

        results = []
        try:
            for i, acc in enumerate(accounts_to_run, 1):
                publish_event({
                    "timestamp": datetime.now().strftime("%H:%M:%S"),
                    "step": "batch_progress",
                    "title": f"Account {i}/{len(accounts_to_run)}",
                    "message": f"Processing {acc.email} (@{acc.username})...",
                    "level": "info",
                    "human_required": False,
                })
                res = run_async_task(session.register_account(acc, headless=False))
                results.append(res)
                time.sleep(3)

            success_cnt = sum(1 for r in results if r.get("success"))
            publish_event({
                "timestamp": datetime.now().strftime("%H:%M:%S"),
                "step": "completed",
                "title": "Batch Finished",
                "message": f"Completed batch processing. {success_cnt} of {len(accounts_to_run)} accounts registered successfully.",
                "level": "success",
                "human_required": False,
                "data": {"total": len(accounts_to_run), "success_count": success_cnt},
            })
        except Exception as e:
            publish_event({
                "timestamp": datetime.now().strftime("%H:%M:%S"),
                "step": "exception",
                "title": "Batch Interrupted",
                "message": str(e),
                "level": "error",
                "human_required": False,
                "data": {},
            })
        finally:
            with active_task_lock:
                is_task_running = False
                current_task_info = {"status": "idle", "task": None, "start_time": None}

    th = threading.Thread(target=batch_runner, daemon=True)
    th.start()

    return jsonify({
        "success": True,
        "message": f"Loaded {len(accounts_to_run)} accounts from Excel. Processing in background.",
    })


@app.route("/api/login", methods=["POST"])
def api_login():
    global is_task_running, current_task_info
    if is_task_running:
        return jsonify({"success": False, "message": "Another automation task is already running."}), 409

    data = request.get_json(force=True, silent=True) or {}
    email = data.get("email", "").strip()
    email_password = data.get("email_password", "").strip()
    username = data.get("username", "").strip()
    password = data.get("password", "").strip()
    imap_server = data.get("imap_server", MXROUTE_DEFAULT_SERVER).strip()
    try:
        imap_port = int(data.get("imap_port", 993))
    except Exception:
        imap_port = 993

    headless = bool(data.get("headless", False))
    proxy = str(data.get("proxy", "")).strip()

    if not username or not password:
        return jsonify({"success": False, "message": "Username and Password are required."}), 400

    account = AccountData(
        email=email or username,
        password=password,
        username=username,
        full_name="Coreteron User",
        email_password=email_password,
        imap_server=imap_server,
        imap_port=imap_port,
        proxy=proxy,
        smspool_api_key=data.get("smspool_api_key") or os.getenv("SMSPOOL_API_KEY", ""),
        smspool_country=data.get("smspool_country", "US"),
    )

    def background_runner():
        global is_task_running, current_task_info
        with active_task_lock:
            is_task_running = True
            current_task_info = {
                "status": "running",
                "task": "login",
                "target": username,
                "start_time": datetime.now().isoformat(),
            }

        session = AutomationSession(
            base_dir=BASE_DIR,
            callback=publish_event,
            human_signal=human_signal_event,
        )

        try:
            res = run_async_task(
                session.login_account(account, headless=headless)
            )
            publish_event({
                "timestamp": datetime.now().strftime("%H:%M:%S"),
                "step": "completed",
                "title": "Login Finished",
                "message": res.get("details", "Finished"),
                "level": "success" if res.get("success") else "error",
                "human_required": False,
                "data": res,
            })
        except Exception as e:
            publish_event({
                "timestamp": datetime.now().strftime("%H:%M:%S"),
                "step": "exception",
                "title": "Login Crashed",
                "message": str(e),
                "level": "error",
                "human_required": False,
                "data": {},
            })
        finally:
            with active_task_lock:
                is_task_running = False
                current_task_info = {"status": "idle", "task": None, "start_time": None}

    th = threading.Thread(target=background_runner, daemon=True)
    th.start()

    return jsonify({"success": True, "message": "Login task initiated in background."})


@app.route("/api/human-action", methods=["POST"])
def api_human_action():
    """Notify the bot that the user has completed the visual checkpoint in the browser."""
    human_signal_event.set()
    publish_event({
        "timestamp": datetime.now().strftime("%H:%M:%S"),
        "step": "human_action_clicked",
        "title": "Operator Confirmed",
        "message": "User signaled human verification completed. Continuing automation...",
        "level": "info",
        "human_required": False,
    })
    return jsonify({"success": True, "message": "Resume signal sent to browser automation."})


@app.route("/api/logs/stream")
def api_logs_stream():
    """Server-Sent Events (SSE) endpoint for real-time frontend event streaming."""
    def event_generator():
        init_data = json.dumps({
            "timestamp": datetime.now().strftime("%H:%M:%S"),
            "step": "connected",
            "title": "Connected",
            "message": "Connected to real-time event stream.",
            "level": "info",
            "human_required": False,
        })
        yield f"data: {init_data}\n\n"

        while True:
            try:
                event = event_queue.get(timeout=15.0)
                yield f"data: {json.dumps(event)}\n\n"
            except queue.Empty:
                yield ": keepalive\n\n"

    return Response(
        event_generator(),
        mimetype="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "X-Accel-Buffering": "no",
            "Connection": "keep-alive",
        },
    )


@app.route("/api/proxy/test", methods=["POST"])
def api_test_proxy():
    """Validates connectivity and outward IP of a proxy endpoint."""
    import base64
    import urllib.error

    data = request.json or {}
    proxy_str = str(data.get("proxy", "")).strip()
    if not proxy_str:
        return jsonify({"success": False, "message": "Proxy string is required."}), 400

    from instagram_engine import parse_proxy_config
    cfg = parse_proxy_config(proxy_str)
    if not cfg:
        return jsonify({"success": False, "message": "Invalid proxy format. Expected http://user:pass@host:port or host:port:user:pass"}), 400

    server = cfg.get("server", "")
    username = cfg.get("username")
    password = cfg.get("password")

    proxy_url = server
    if username and password:
        parts = server.split("://")
        scheme = parts[0]
        host = parts[1]
        proxy_url = f"{scheme}://{username}:{password}@{host}"

    proxy_handler = urllib.request.ProxyHandler({"http": proxy_url, "https": proxy_url})
    handlers = [proxy_handler]

    if username and password:
        password_mgr = urllib.request.HTTPPasswordMgrWithDefaultRealm()
        password_mgr.add_password(None, server, username, password)
        auth_handler = urllib.request.ProxyBasicAuthHandler(password_mgr)
        handlers.append(auth_handler)

    opener = urllib.request.build_opener(*handlers)
    req = urllib.request.Request("http://api.ipify.org?format=json", headers={"User-Agent": "CoreteronProxyTester/1.0"})
    if username and password:
        auth_bytes = f"{username}:{password}".encode("utf-8")
        req.add_header("Proxy-Authorization", "Basic " + base64.b64encode(auth_bytes).decode("utf-8"))

    start_t = time.time()
    try:
        with opener.open(req, timeout=10) as resp:
            data_resp = json.loads(resp.read().decode())
            latency_ms = round((time.time() - start_t) * 1000)
            return jsonify({
                "success": True,
                "ip": data_resp.get("ip"),
                "latency_ms": latency_ms,
                "message": f"Proxy active. External IP: {data_resp.get('ip')} ({latency_ms}ms)",
            })
    except urllib.error.HTTPError as e:
        if e.code == 407:
            return jsonify({
                "success": False,
                "message": "Proxy Authentication Required (HTTP 407). The proxy server rejected your credentials. Please verify your username and password, or check if your IP must be whitelisted in your proxy provider dashboard.",
            }), 400
        return jsonify({"success": False, "message": f"Proxy HTTP Error {e.code}: {e.reason}"}), 400
    except Exception as e:
        err_msg = str(e)
        if "407" in err_msg:
            return jsonify({
                "success": False,
                "message": "Proxy Authentication Required (HTTP 407). The proxy server rejected your credentials. Please verify your username and password, or check if your IP must be whitelisted in your proxy provider dashboard.",
            }), 400
        return jsonify({"success": False, "message": f"Proxy connection check failed: {err_msg}"}), 500


@app.route("/api/template")
def download_template():
    """Download default Excel template."""
    if TEMPLATE_EXCEL.exists():
        return send_file(str(TEMPLATE_EXCEL), as_attachment=True, download_name="coreteron_accounts_template.xlsx")
    return jsonify({"success": False, "message": "Template file not found."}), 404


@app.route("/api/smspool/balance", methods=["GET", "POST"])
def api_smspool_balance():
    """Check SMSPool account balance."""
    payload = request.get_json(force=True, silent=True) or {}
    key = payload.get("key") or request.args.get("key") or os.getenv("SMSPOOL_API_KEY", "")
    client = SMSPoolClient(api_key=key)
    res = client.check_balance()
    return jsonify(res)


@app.route("/api/smspool/countries", methods=["GET"])
def api_smspool_countries():
    """Retrieve list of supported countries for SMSPool."""
    client = SMSPoolClient()
    countries = client.retrieve_countries()
    if not countries:
        countries = [
            {"ID": 1, "name": "United States", "short_name": "US", "cc": "1"},
            {"ID": 2, "name": "United Kingdom", "short_name": "GB", "cc": "44"},
            {"ID": 3, "name": "Canada", "short_name": "CA", "cc": "1"},
            {"ID": 4, "name": "Australia", "short_name": "AU", "cc": "61"},
            {"ID": 5, "name": "Germany", "short_name": "DE", "cc": "49"},
            {"ID": 6, "name": "France", "short_name": "FR", "cc": "33"},
            {"ID": 7, "name": "Netherlands", "short_name": "NL", "cc": "31"},
        ]
    return jsonify({"success": True, "countries": countries})


@app.route("/api/smspool/purchase", methods=["POST"])
def api_smspool_purchase():
    """Order a temporary SMS verification phone number for Instagram."""
    payload = request.get_json(force=True, silent=True) or {}
    key = payload.get("key") or os.getenv("SMSPOOL_API_KEY", "")
    country = payload.get("country", "US")
    service = str(payload.get("service", "457"))  # 457 = Instagram / Threads
    pool = payload.get("pool")
    max_price = payload.get("max_price")

    client = SMSPoolClient(api_key=key)
    res = client.purchase_sms(country=country, service=service, pool=pool, max_price=max_price)
    return jsonify(res), (200 if res.get("success") else 400)


@app.route("/api/smspool/check", methods=["POST"])
def api_smspool_check():
    """Check incoming SMS code for an active order."""
    payload = request.get_json(force=True, silent=True) or {}
    key = payload.get("key") or os.getenv("SMSPOOL_API_KEY", "")
    order_id = payload.get("order_id") or payload.get("orderid")
    if not order_id:
        return jsonify({"success": False, "message": "order_id is required."}), 400

    client = SMSPoolClient(api_key=key)
    res = client.check_sms(str(order_id))
    return jsonify(res)


@app.route("/api/smspool/cancel", methods=["POST"])
def api_smspool_cancel():
    """Cancel an active SMS order to trigger a refund."""
    payload = request.get_json(force=True, silent=True) or {}
    key = payload.get("key") or os.getenv("SMSPOOL_API_KEY", "")
    order_id = payload.get("order_id") or payload.get("orderid")
    if not order_id:
        return jsonify({"success": False, "message": "order_id is required."}), 400

    client = SMSPoolClient(api_key=key)
    res = client.cancel_sms(str(order_id))
    return jsonify(res)


@app.route("/api/smspool/save-key", methods=["POST"])
def api_smspool_save_key():
    """Persist SMSPool API key to current runtime and .env configuration file."""
    payload = request.get_json(force=True, silent=True) or {}
    key = str(payload.get("key", "")).strip()
    if not key:
        return jsonify({"success": False, "message": "API key cannot be empty."}), 400

    os.environ["SMSPOOL_API_KEY"] = key

    # Persist to .env
    env_path = BASE_DIR / ".env"
    try:
        lines = []
        if env_path.exists():
            with open(env_path, "r", encoding="utf-8") as f:
                lines = f.readlines()
        found = False
        new_lines = []
        for line in lines:
            if line.startswith("SMSPOOL_API_KEY="):
                new_lines.append(f"SMSPOOL_API_KEY={key}\n")
                found = True
            else:
                new_lines.append(line)
        if not found:
            new_lines.append(f"SMSPOOL_API_KEY={key}\n")
        with open(env_path, "w", encoding="utf-8") as f:
            f.writelines(new_lines)
    except Exception as e:
        logger.warning("Could not persist SMSPOOL_API_KEY to .env: %s", e)

    return jsonify({"success": True, "message": "SMSPool API key saved and activated."})


def start_server(host: str = "127.0.0.1", port: int = 5050, debug: bool = False):
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s | %(levelname)-7s | %(message)s",
    )
    print("=" * 65)
    print("  CORETERON INSTAGRAM SUITE WEB DASHBOARD")
    print(f"  Running locally at: http://{host}:{port}")
    print("  MXroute Sub-second IMAP Verification: ENABLED")
    print("=" * 65)
    app.run(host=host, port=port, debug=debug, threaded=True)


if __name__ == "__main__":
    configured_port = int(os.getenv("PORT", "5050"))
    start_server(port=configured_port)
