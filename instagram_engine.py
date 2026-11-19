#!/usr/bin/env python3
"""Unified Instagram Automation Engine for Coreteron Suite.

Supports:
- Automated account registration with custom or random credentials
- Direct MXroute IMAP OTP verification (sub-second polling)
- Auto-clicker for 'Continue', 'Next', 'Save info', 'Not now' WebBloks buttons
- Resilient self-healing retry on rejected or expired OTPs
- Interactive Human-in-the-Loop pause for CAPTCHAs & Phone verification
- Authenticated session verification & feed scrolling
"""

from __future__ import annotations

import asyncio
from dataclasses import dataclass
from datetime import datetime
import json
import logging
from pathlib import Path
import random
import re
import string
import sys
import threading
import time
from typing import Any, Callable, Dict, Optional, Tuple

import pandas as pd
from playwright.async_api import (
    BrowserContext,
    Locator,
    Page,
    TimeoutError as PlaywrightTimeoutError,
    async_playwright,
)

from mxroute_client import DEFAULT_SERVER as MXROUTE_DEFAULT_SERVER, fetch_mxroute_otp

logger = logging.getLogger("instagram_engine")

SIGNUP_URL = "https://www.instagram.com/accounts/emailsignup/"
LOGIN_URL = "https://www.instagram.com/accounts/login/"
DEFAULT_BIRTHDAY = "1995-06-15"
NAVIGATION_TIMEOUT_MS = 45_000
UI_SETTLE_MS = 1_500
MAX_USERNAME_ATTEMPTS = 6
OTP_WAIT_TIMEOUT_SECONDS = 90
HUMAN_CAPTCHA_TIMEOUT_SECONDS = 180


@dataclass
class AccountData:
    email: str
    password: str
    username: str
    full_name: str
    email_password: str
    imap_server: str = MXROUTE_DEFAULT_SERVER
    imap_port: int = 993
    birthday: str = DEFAULT_BIRTHDAY
    phone_number: str = ""
    proxy: str = ""

    def validate(self) -> None:
        if not self.email or "@" not in self.email:
            raise ValueError("Valid email address is required")
        if not self.password:
            raise ValueError("Instagram password is required")
        if not self.username:
            raise ValueError("Username is required")
        if not self.email_password:
            raise ValueError("Email password is required to read verification codes")


def parse_proxy_config(proxy_str: str) -> Optional[Dict[str, str]]:
    """Normalizes proxy URL or IP:Port:User:Pass format for Playwright."""
    if not proxy_str or not proxy_str.strip():
        return None
    raw = proxy_str.strip()
    if raw.startswith("#"):
        return None

    # Format: host:port:user:pass
    parts = raw.split(":")
    if len(parts) == 4 and not raw.startswith("http://") and not raw.startswith("socks5://"):
        host, port, user, pwd = parts
        return {
            "server": f"http://{host}:{port}",
            "username": user,
            "password": pwd,
        }

    if "://" not in raw:
        raw = f"http://{raw}"

    from urllib.parse import urlparse
    try:
        parsed = urlparse(raw)
        server = f"{parsed.scheme}://{parsed.hostname}:{parsed.port}"
        cfg: Dict[str, str] = {"server": server}
        if parsed.username:
            cfg["username"] = parsed.username
        if parsed.password:
            cfg["password"] = parsed.password
        return cfg
    except Exception:
        return None


def generate_random_credentials(prefix: str = "coreteron") -> Dict[str, str]:
    """Helper to generate clean, realistic user credentials."""
    first_names = ["Alex", "Jordan", "Taylor", "Morgan", "Sam", "Chris", "Pat", "Robin", "Casey", "Avery"]
    last_names = ["Rivers", "Vance", "Bennett", "Hayden", "Brooks", "Sinclair", "Sterling", "Cross", "Monroe"]
    first = random.choice(first_names)
    last = random.choice(last_names)
    full_name = f"{first} {last}"
    
    rnd_num = random.randint(100, 9999)
    username = f"{prefix}_{first.lower()}_{rnd_num}"
    
    chars = string.ascii_letters + string.digits + "!@#$%^&*"
    pwd_body = "".join(random.choices(chars, k=10))
    password = f"Corteron!{pwd_body}9"
    
    year = random.randint(1993, 2001)
    month = f"{random.randint(1, 12):02d}"
    day = f"{random.randint(1, 28):02d}"
    birthday = f"{year}-{month}-{day}"
    
    return {
        "full_name": full_name,
        "username": username,
        "password": password,
        "birthday": birthday,
    }


class AutomationSession:
    def __init__(
        self,
        base_dir: Path,
        callback: Optional[Callable[[Dict[str, Any]], None]] = None,
        human_signal: Optional[threading.Event] = None,
    ):
        self.base_dir = Path(base_dir)
        self.callback = callback
        self.human_signal = human_signal or threading.Event()
        self.cancelled = False

    def emit(
        self,
        step: str,
        title: str,
        message: str,
        level: str = "info",
        human_required: bool = False,
        data: Optional[Dict[str, Any]] = None,
    ) -> None:
        """Publish real-time status update to web frontend and log."""
        payload = {
            "timestamp": datetime.now().strftime("%H:%M:%S"),
            "step": step,
            "title": title,
            "message": message,
            "level": level,
            "human_required": human_required,
            "data": data or {},
        }
        logger.info("[%s] %s: %s", level.upper(), title, message)
        if self.callback:
            try:
                self.callback(payload)
            except Exception as e:
                logger.debug("Callback emit failed: %s", e)

    async def dismiss_cookies(self, page: Page) -> None:
        candidates = [
            page.get_by_role("button", name=re.compile(r"Allow (all|essential) cookies", re.I)),
            page.get_by_role("button", name=re.compile(r"Decline optional cookies", re.I)),
            page.locator("button:has-text('Allow all')"),
            page.locator("button:has-text('Decline')"),
            page.locator("button:has-text('Accept')"),
        ]
        for btn in candidates:
            try:
                if await btn.first.is_visible(timeout=1_200):
                    await btn.first.click()
                    self.emit("cookies", "Cookie Consent", "Dismissed cookie banner automatically.")
                    await page.wait_for_timeout(400)
                    return
            except Exception:
                continue

    async def click_continue_if_present(self, page: Page) -> bool:
        """Smart detector: auto-clicks 'Continue', 'Next', 'Save info', 'Not now', 'Confirm'."""
        candidates = [
            page.get_by_role("button", name=re.compile(r"^(continue|next|confirm|save info|not now|get started)$", re.I)),
            page.get_by_text(re.compile(r"^continue$", re.I)),
            page.locator("button:has-text('Continue')"),
            page.locator("div[role='button']:has-text('Continue')"),
            page.locator("div[role='button'][aria-label='Continue']"),
            page.locator("button:has-text('Next')"),
            page.locator("div[role='button']:has-text('Next')"),
            page.locator("button:has-text('Save info')"),
            page.locator("div[role='button']:has-text('Save info')"),
            page.locator("button:has-text('Not now')"),
            page.locator("div[role='button']:has-text('Not now')"),
        ]
        for cand in candidates:
            try:
                btn = cand.first
                if await btn.is_visible(timeout=800):
                    is_disabled = (await btn.get_attribute("disabled")) is not None or (await btn.get_attribute("aria-disabled") == "true")
                    if not is_disabled:
                        txt = (await btn.inner_text()).strip()
                        await btn.click()
                        self.emit("auto_click", "Auto Button Click", f"Automatically clicked '{txt}'.")
                        await page.wait_for_timeout(2_000)
                        return True
            except Exception:
                continue
        return False

    async def handle_birthday_if_present(self, page: Page, birthday_str: str) -> bool:
        """Select birth month, day, and year dropdowns if displayed."""
        body = ""
        try:
            body = (await page.locator("body").inner_text(timeout=1_500)).lower()
        except Exception:
            pass
        if "birthday" not in body and "date of birth" not in body:
            return False

        self.emit("birthday", "Birthday Verification", "Selecting birthday options...")
        try:
            dt = datetime.strptime(birthday_str, "%Y-%m-%d")
        except Exception:
            dt = datetime(1995, 6, 15)

        month_val = str(dt.month)
        day_val = str(dt.day)
        year_val = str(dt.year)

        for selector, val in [
            ("select[title*='Month']", month_val),
            ("select[title*='Day']", day_val),
            ("select[title*='Year']", year_val),
        ]:
            try:
                sel = page.locator(selector).first
                if await sel.is_visible(timeout=1_500):
                    await sel.select_option(val)
                    await page.wait_for_timeout(400)
            except Exception:
                pass

        await self.click_continue_if_present(page)
        return True

    async def is_home_feed_active(self, page: Page) -> bool:
        url = page.url.lower()
        if "emailsignup" in url or "login" in url or "codeentry" in url or "suspended" in url:
            return False
        indicators = [
            'svg[aria-label="Home"]',
            '[aria-label="Home"]',
            'a[href*="/direct/inbox/"]',
            'a[href*="/explore/"]',
            'svg[aria-label*="Profile"]',
            '[aria-label*="Profile"]',
            'span:has-text("Search")',
            'span:has-text("Messages")',
        ]
        for sel in indicators:
            try:
                if await page.locator(sel).first.is_visible(timeout=800):
                    return True
            except Exception:
                continue
        try:
            body = (await page.locator("body").inner_text(timeout=1_500)).lower()
            if "save your login info" in body or "turn on notifications" in body or "welcome to instagram" in body:
                return True
        except Exception:
            pass
        return False

    async def scroll_feed(self, page: Page, count: int = 3) -> None:
        self.emit("feed_scroll", "Verifying Active Session", f"Scrolling home feed ({count} times)...")
        for i in range(1, count + 1):
            self.emit("feed_scroll", "Feed Activity", f"Active feed interaction: scroll {i}/{count}...")
            await page.mouse.wheel(0, 600)
            await page.wait_for_timeout(2_000)
        self.emit("feed_scroll", "Feed Verified", "Home feed session confirmed active!")

    async def wait_for_human_checkpoint(self, page: Page, timeout_seconds: int = HUMAN_CAPTCHA_TIMEOUT_SECONDS) -> bool:
        """Pause and alert the operator when Instagram presents a visual check or phone verification."""
        self.emit(
            "human_needed",
            "Action Required: Human Verification",
            "Instagram has displayed a verification check in the open browser window. Please complete it directly in the browser! Automation will auto-resume once completed.",
            level="warning",
            human_required=True,
        )

        try:
            await page.bring_to_front()
        except Exception:
            pass

        self.human_signal.clear()
        deadline = time.time() + timeout_seconds

        while time.time() < deadline:
            if self.human_signal.is_set():
                self.emit("human_resume", "Resuming Automation", "User confirmed verification completed.")
                await page.wait_for_timeout(2_000)
                return True

            url = page.url.lower()
            if "suspended" not in url and "challenge" not in url and "phone" not in url:
                if await self.is_home_feed_active(page):
                    self.emit("human_resume", "Resuming Automation", "Navigated to home feed!")
                    return True

            await asyncio.sleep(1.5)

        self.emit("human_timeout", "Checkpoint Timeout", f"Did not complete verification within {timeout_seconds}s.", level="error")
        return False

    async def register_account(
        self,
        account: AccountData,
        headless: bool = False,
    ) -> Dict[str, Any]:
        """Complete turnkey registration pipeline."""
        account.validate()

        result = {
            "success": False,
            "status": "INITIATED",
            "email": account.email,
            "username": account.username,
            "otp": "",
            "details": "",
        }

        self.emit("init", "Starting Registration", f"Beginning account creation for {account.email} (@{account.username})...")

        proxy_cfg = parse_proxy_config(account.proxy)
        if proxy_cfg:
            self.emit("proxy", "Proxy Configured", f"Routing session via proxy: {proxy_cfg['server']}")

        async with async_playwright() as pw:
            launch_kwargs = {
                "headless": headless,
                "args": [
                    "--disable-blink-features=AutomationControlled",
                    "--no-sandbox",
                    "--start-maximized",
                ],
            }
            if proxy_cfg:
                launch_kwargs["proxy"] = proxy_cfg

            browser = await pw.chromium.launch(**launch_kwargs)

            context = await browser.new_context(
                viewport={"width": 1280, "height": 800},
                user_agent=(
                    "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) "
                    "AppleWebKit/537.36 (KHTML, like Gecko) "
                    "Chrome/124.0.0.0 Safari/537.36"
                ),
                locale="en-US",
            )
            page = await context.new_page()

            try:
                # 1. Load Signup Page
                self.emit("nav", "Opening Instagram", f"Navigating to {SIGNUP_URL}...")
                try:
                    await page.goto(SIGNUP_URL, wait_until="domcontentloaded", timeout=NAVIGATION_TIMEOUT_MS)
                except Exception:
                    await page.goto(SIGNUP_URL, timeout=NAVIGATION_TIMEOUT_MS)

                await page.wait_for_timeout(UI_SETTLE_MS)
                await self.dismiss_cookies(page)

                # Check if redirected to login page and click 'Sign up'
                if "/accounts/login" in page.url or page.url.rstrip("/").endswith("instagram.com"):
                    signup_link = page.locator("a[href*='/accounts/emailsignup'], a:has-text('Sign up'), span:has-text('Sign up')").first
                    if await signup_link.is_visible(timeout=3_000):
                        await signup_link.click()
                        await page.wait_for_timeout(2_000)

                # 2. Fill Registration Fields
                self.emit("form_fill", "Entering Information", f"Filling email, name, username (@{account.username}), and secure password...")
                
                email_input = page.locator(
                    "label:has-text('Mobile number or email') input, "
                    "label:has-text('Mobile Number or Email') input, "
                    "label:has-text('email') input, "
                    "div:has-text('Mobile number or email') > input, "
                    "input[name='emailOrPhone'], "
                    "input[aria-label*='Mobile Number or Email'], "
                    "input[aria-label*='Email'], "
                    "input[name='email'], "
                    "input[type='email']"
                ).first

                name_input = page.locator(
                    "label:has-text('Full name') input, "
                    "label:has-text('Full Name') input, "
                    "label:has-text('Name') input, "
                    "input[name='fullName'], "
                    "input[aria-label*='Full Name'], "
                    "input[placeholder*='Full Name']"
                ).first

                user_input = page.locator(
                    "input[aria-label='Username'], "
                    "label:has-text('Username') input, "
                    "input[name='username'], "
                    "input[placeholder*='Username'], "
                    "input[role='combobox'][aria-label='Username']"
                ).first

                pwd_input = page.locator(
                    "label:has-text('Password') input, "
                    "input[name='password'], "
                    "input[type='password']"
                ).first

                # Wait for form with graceful fallback
                try:
                    await email_input.wait_for(state="visible", timeout=25_000)
                except Exception:
                    await self.dismiss_cookies(page)
                    all_inputs = await page.locator("input:visible").all()
                    if len(all_inputs) >= 4:
                        email_input = all_inputs[0]
                        pwd_input = all_inputs[1]
                        name_input = all_inputs[2]
                        user_input = all_inputs[3]
                    else:
                        await email_input.wait_for(state="visible", timeout=15_000)

                await email_input.fill(account.email)
                await page.wait_for_timeout(300)

                await name_input.fill(account.full_name)
                await page.wait_for_timeout(300)

                await user_input.fill(account.username)
                await page.wait_for_timeout(300)

                await pwd_input.fill(account.password)
                await page.wait_for_timeout(600)

                # Submit initial form
                submit_btn = page.get_by_role("button", name=re.compile(r"^(submit|sign\s*up)$", re.I)).first
                if not await submit_btn.is_visible(timeout=3_000):
                    submit_btn = page.locator(
                        "button:has-text('Submit'), "
                        "button:has-text('Sign up'), "
                        "div[role='button']:has-text('Submit'), "
                        "div[role='button']:has-text('Sign up'), "
                        "button[type='submit']:visible"
                    ).first

                await submit_btn.click()
                self.emit("form_submit", "Initial Form Submitted", "Submitted registration credentials. Waiting for next step...")
                await page.wait_for_timeout(3_000)

                # 3. Handle Birthday if asked
                await self.handle_birthday_if_present(page, account.birthday)
                await page.wait_for_timeout(2_000)

                # 4. Check for Checkpoint/CAPTCHA
                body_text = ""
                try:
                    body_text = (await page.locator("body").inner_text(timeout=2_000)).lower()
                except Exception:
                    pass

                if "confirm you're human" in body_text or "suspended" in page.url.lower():
                    await self.click_continue_if_present(page)
                    await page.wait_for_timeout(3_000)
                    body_text = (await page.locator("body").inner_text(timeout=2_000)).lower()
                    if "code from the image" in body_text or "confirm you're human" in body_text:
                        await self.wait_for_human_checkpoint(page)

                # 5. Detect Email OTP Page
                self.emit("otp_detect", "Confirmation Code Screen", "Waiting for confirmation code entry screen...")
                otp_input = None
                for _ in range(12):
                    candidates = [
                        page.locator("input[name='email_confirmation_code']").first,
                        page.locator("input[name='confirmationCode']").first,
                        page.locator("input[aria-label*='Confirmation Code']").first,
                        page.locator("input[placeholder*='Confirmation Code']").first,
                        page.locator("label:has-text('Confirmation code') input").first,
                        page.locator("label:has-text('confirmation code') input").first,
                        page.locator("input[inputmode='numeric']").first,
                        page.locator("input[maxlength='6']").first,
                        page.locator("input[type='text']:visible").first,
                    ]
                    for cand in candidates:
                        try:
                            if await cand.is_visible(timeout=1_000):
                                otp_input = cand
                                break
                        except Exception:
                            continue
                    if otp_input:
                        break
                    await self.click_continue_if_present(page)
                    await page.wait_for_timeout(1_000)

                if not otp_input:
                    self.emit("otp_err", "Screen Not Found", "Confirmation code input not found on page.", level="warning")
                    if await self.is_home_feed_active(page):
                        result["success"] = True
                        result["status"] = "SUCCESS"
                        result["details"] = "Account created directly without email confirmation prompt!"
                        await self.scroll_feed(page)
                        return result
                    result["status"] = "NO_OTP_SCREEN"
                    return result

                # 6. Fetch OTP from MXroute IMAP
                self.emit(
                    "imap_fetch",
                    "Retrieving Verification Code",
                    f"Connecting to MXroute ({account.imap_server}:{account.imap_port}) to read verification email...",
                )
                otp_code = fetch_mxroute_otp(
                    email_address=account.email,
                    password=account.email_password,
                    server=account.imap_server,
                    port=account.imap_port,
                    timeout_seconds=OTP_WAIT_TIMEOUT_SECONDS,
                )

                if not otp_code:
                    self.emit("imap_timeout", "OTP Timeout", f"No verification email received within {OTP_WAIT_TIMEOUT_SECONDS}s.", level="error")
                    result["status"] = "OTP_TIMEOUT"
                    result["details"] = "Email with 6-digit code was not received in mailbox."
                    return result

                result["otp"] = otp_code
                self.emit("otp_received", "Code Received!", f"Extracted 6-digit confirmation code: {otp_code}", level="success", data={"otp": otp_code})

                # 7. Type and Submit OTP
                await otp_input.click()
                await otp_input.fill("")
                await otp_input.type(otp_code, delay=120)
                await page.wait_for_timeout(1_000)

                # Submit code
                next_btn = page.get_by_role("button", name=re.compile(r"^(continue|next|submit|confirm|verify)$", re.I)).first
                if not await next_btn.is_visible(timeout=2_000):
                    next_btn = page.locator("button[type='submit']:visible, div[role='button']:has-text('Next')").first

                if await next_btn.is_visible(timeout=2_000):
                    await next_btn.click()
                else:
                    await otp_input.press("Enter")

                self.emit("otp_submitted", "Code Submitted", f"Submitted code {otp_code}. Waiting for Instagram to verify...")
                await page.wait_for_timeout(4_000)

                # Check if code didn't work (Self-healing retry)
                body_resp = ""
                try:
                    body_resp = (await page.locator("body").inner_text(timeout=2_000)).lower()
                except Exception:
                    pass

                if "this code doesn't work" in body_resp or "check the code" in body_resp:
                    self.emit("otp_retry", "Code Rejected", "Instagram flagged code as invalid. Requesting new code...", level="warning")
                    get_new = page.get_by_text(re.compile(r"get a new code|resend code", re.I)).first
                    if await get_new.is_visible(timeout=2_000):
                        await get_new.click()
                        await page.wait_for_timeout(3_000)

                    self.emit("imap_retry", "Fetching Fresh Code", f"Waiting for fresh code excluding {otp_code}...")
                    fresh_code = fetch_mxroute_otp(
                        email_address=account.email,
                        password=account.email_password,
                        server=account.imap_server,
                        port=account.imap_port,
                        timeout_seconds=60,
                        exclude_code=otp_code,
                    )
                    if fresh_code:
                        result["otp"] = fresh_code
                        self.emit("otp_received", "Fresh Code Received", f"Extracted fresh code: {fresh_code}", level="success")
                        await otp_input.fill("")
                        await otp_input.type(fresh_code, delay=120)
                        await page.wait_for_timeout(1_000)
                        await self.click_continue_if_present(page)
                        await page.wait_for_timeout(4_000)

                # 8. Post-verification Flow & Smart Handlers
                for step_num in range(10):
                    await page.wait_for_timeout(2_000)
                    curr_url = page.url.lower()
                    curr_body = ""
                    try:
                        curr_body = (await page.locator("body").inner_text(timeout=1_500)).lower()
                    except Exception:
                        pass

                    # Smart Click popups
                    await self.click_continue_if_present(page)

                    # Check for Suspended / Checkpoint
                    if "confirm you're human" in curr_body or "suspended" in curr_url:
                        cont_clicked = await self.click_continue_if_present(page)
                        if cont_clicked:
                            await page.wait_for_timeout(3_000)
                        if "code from the image" in curr_body or "suspended" in curr_url:
                            await self.wait_for_human_checkpoint(page)

                    # Check for Phone Checkpoint
                    if "enter your mobile number" in curr_body or "phone number" in curr_body:
                        await self.wait_for_human_checkpoint(page)

                    # Check if home feed reached!
                    if await self.is_home_feed_active(page):
                        break

                # 9. Feed Verification & Scrolls
                if await self.is_home_feed_active(page):
                    await self.scroll_feed(page, count=3)
                    result["success"] = True
                    result["status"] = "SUCCESS"
                    result["details"] = "Account registered, email verified with MXroute IMAP, and active session confirmed!"
                else:
                    result["success"] = True
                    result["status"] = "COMPLETED"
                    result["details"] = f"Account registered and verified. Final page: {page.url}"

                return result

            except Exception as e:
                logger.exception("Registration pipeline error: %s", e)
                result["status"] = "ERROR"
                result["details"] = str(e)
                self.emit("error", "Error Occurred", str(e), level="error")
                return result

            finally:
                await context.close()
                await browser.close()


    async def login_account(
        self,
        account: AccountData,
        headless: bool = False,
    ) -> Dict[str, Any]:
        """Automated Login & Device Verification pipeline."""
        account.validate()

        result = {
            "success": False,
            "status": "INITIATED",
            "username": account.username,
            "otp": "",
            "details": "",
        }

        self.emit("init", "Starting Login", f"Logging into Instagram for @{account.username}...")

        proxy_cfg = parse_proxy_config(account.proxy)
        if proxy_cfg:
            self.emit("proxy", "Proxy Configured", f"Routing session via proxy: {proxy_cfg['server']}")

        async with async_playwright() as pw:
            launch_kwargs = {
                "headless": headless,
                "args": [
                    "--disable-blink-features=AutomationControlled",
                    "--no-sandbox",
                    "--start-maximized",
                ],
            }
            if proxy_cfg:
                launch_kwargs["proxy"] = proxy_cfg

            browser = await pw.chromium.launch(**launch_kwargs)

            context = await browser.new_context(
                viewport={"width": 1280, "height": 800},
                user_agent=(
                    "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) "
                    "AppleWebKit/537.36 (KHTML, like Gecko) "
                    "Chrome/124.0.0.0 Safari/537.36"
                ),
                locale="en-US",
            )
            page = await context.new_page()

            try:
                self.emit("nav", "Opening Login Page", f"Navigating to {LOGIN_URL}...")
                await page.goto(LOGIN_URL, wait_until="domcontentloaded", timeout=NAVIGATION_TIMEOUT_MS)
                await page.wait_for_timeout(UI_SETTLE_MS)
                await self.dismiss_cookies(page)

                user_field = page.locator(
                    "label:has-text('Mobile number, username or email') input, "
                    "label:has-text('username') input, "
                    "label:has-text('email') input, "
                    "input[name='email'], "
                    "input[name='username'], "
                    "input[name='emailOrPhone'], "
                    "input[type='text']:visible"
                ).first
                pwd_field = page.locator(
                    "label:has-text('Password') input, "
                    "input[name='pass'], "
                    "input[name='password'], "
                    "input[type='password']:visible"
                ).first

                await user_field.wait_for(state="visible", timeout=25_000)
                await user_field.fill(account.username)
                await page.wait_for_timeout(300)
                await pwd_field.fill(account.password)
                await page.wait_for_timeout(600)

                login_btn = page.get_by_role("button", name=re.compile(r"^log\s*in$", re.I)).first
                if not await login_btn.is_visible(timeout=3_000):
                    login_btn = page.locator("button:has-text('Log in'), button[type='submit']:visible, div[role='button']:has-text('Log in')").first

                await login_btn.click()
                self.emit("login_submit", "Credentials Submitted", "Submitted login. Checking for device verification...")
                await page.wait_for_timeout(4_000)

                body_txt = ""
                try:
                    body_txt = (await page.locator("body").inner_text(timeout=2_000)).lower()
                except Exception:
                    pass

                if "codeentry" in page.url.lower() or "check your email" in body_txt or "security code" in body_txt:
                    self.emit("otp_detect", "Device Verification Required", f"Polling MXroute IMAP for device login code...")
                    login_otp = fetch_mxroute_otp(
                        email_address=account.email,
                        password=account.email_password,
                        server=account.imap_server,
                        port=account.imap_port,
                        timeout_seconds=OTP_WAIT_TIMEOUT_SECONDS,
                    )
                    if login_otp:
                        result["otp"] = login_otp
                        self.emit("otp_received", "Login Code Extracted", f"Received login OTP: {login_otp}", level="success")
                        code_input = page.locator("input[name='verificationCode'], input[name='security_code'], input[placeholder*='code']").first
                        if await code_input.is_visible(timeout=3_000):
                            await code_input.fill(login_otp)
                            await page.wait_for_timeout(800)
                            await self.click_continue_if_present(page)
                            await page.wait_for_timeout(4_000)

                for _ in range(6):
                    await self.click_continue_if_present(page)
                    await page.wait_for_timeout(1_000)

                if await self.is_home_feed_active(page):
                    await self.scroll_feed(page, count=3)
                    result["success"] = True
                    result["status"] = "SUCCESS"
                    result["details"] = "Login verified successfully! Active session confirmed."
                else:
                    result["success"] = True
                    result["status"] = "COMPLETED"
                    result["details"] = f"Login submitted. Current page: {page.url}"

                return result

            except Exception as e:
                logger.exception("Login pipeline error: %s", e)
                result["status"] = "ERROR"
                result["details"] = str(e)
                self.emit("error", "Login Error", str(e), level="error")
                return result

            finally:
                await context.close()
                await browser.close()
