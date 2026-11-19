#!/usr/bin/env python3
"""MXroute REST API and IMAP Client.

Handles:
1. Automated email mailbox provisioning via MXroute REST API:
   https://api.mxroute.com/docs
2. Polling for incoming Instagram verification codes over IMAP:
   Server: witcher.mxrouting.net, Port: 993 (SSL/TLS)
"""

from __future__ import annotations

import email
from email.header import decode_header, make_header
import imaplib
import json
import logging
import os
import re
import sys
import time
from typing import Any, Dict, List, Optional, Tuple
import urllib.error
import urllib.parse
import urllib.request

logger = logging.getLogger("mxroute_client")

API_BASE_URL = "https://api.mxroute.com"
DEFAULT_SERVER = "witcher.mxrouting.net"
DEFAULT_USERNAME = "ggcvwsombx"
DEFAULT_IMAP_PORT = 993

OTP_REGEX = re.compile(r"(?<!\d)(\d{3}\s?\d{3}|\d{6})(?!\d)")


def decode_header_val(val: str | bytes | None) -> str:
    if not val:
        return ""
    try:
        return str(make_header(decode_header(val)))
    except Exception:
        if isinstance(val, bytes):
            return val.decode("utf-8", errors="replace")
        return str(val)


def extract_plain_text(msg: email.message.Message) -> str:
    plain_parts = []
    html_parts = []

    parts = msg.walk() if msg.is_multipart() else [msg]
    for part in parts:
        if "attachment" in str(part.get("Content-Disposition", "")):
            continue
        ctype = part.get_content_type()
        if ctype not in ("text/plain", "text/html"):
            continue

        payload = part.get_payload(decode=True)
        if not payload:
            continue

        charset = part.get_content_charset() or "utf-8"
        text = payload.decode(charset, errors="replace")

        if ctype == "text/plain":
            plain_parts.append(text)
        elif ctype == "text/html":
            html_parts.append(text)

    if plain_parts:
        return "\n".join(plain_parts)

    raw_html = "\n".join(html_parts)
    clean = re.sub(r"(?is)<(script|style).*?>.*?</\1>", "", raw_html)
    clean = re.sub(r"(?i)<br\s*/?>|</p>|</div>|</tr>|</h\d>", "\n", clean)
    clean = re.sub(r"<[^>]+>", "", clean)
    return clean


class MXRouteAPIClient:
    """Client for MXroute REST API."""

    def __init__(
        self,
        api_key: str,
        server: str = DEFAULT_SERVER,
        username: str = DEFAULT_USERNAME,
    ):
        self.api_key = api_key.strip()
        self.server = server.strip()
        self.username = username.strip()

    def _headers(self) -> Dict[str, str]:
        return {
            "Content-Type": "application/json",
            "Accept": "application/json",
            "X-Server": self.server,
            "X-Username": self.username,
            "X-API-Key": self.api_key,
        }

    def _request(
        self,
        method: str,
        endpoint: str,
        data: Optional[Dict[str, Any]] = None,
    ) -> Dict[str, Any]:
        url = f"{API_BASE_URL}{endpoint}"
        body_bytes = json.dumps(data).encode("utf-8") if data is not None else None

        req = urllib.request.Request(url, data=body_bytes, headers=self._headers(), method=method)
        logger.debug("MXroute API %s %s", method, url)

        try:
            with urllib.request.urlopen(req, timeout=15) as resp:
                status = resp.status
                raw = resp.read().decode("utf-8")
                if status in (200, 201) and raw:
                    return json.loads(raw)
                return {"success": True, "status": status}
        except urllib.error.HTTPError as e:
            err_body = e.read().decode("utf-8", errors="replace")
            try:
                parsed = json.loads(err_body)
            except Exception:
                parsed = {"raw": err_body}
            logger.error("MXroute API Error [%s]: %s", e.code, parsed)
            raise RuntimeError(f"MXroute API Error ({e.code}): {parsed}") from e

    def list_domains(self) -> List[str]:
        """List active domains on the MXroute account."""
        res = self._request("GET", "/domains")
        return res.get("data", [])

    def create_email_account(
        self,
        domain: str,
        username: str,
        password: str,
        quota_mb: int = 1024,
        daily_limit: int = 9600,
    ) -> Dict[str, Any]:
        """
        Create a new email account under domain.
        Example: create_email_account("corteron.com", "user01", "Password123!")
        Creates user01@corteron.com
        """
        endpoint = f"/domains/{domain}/email-accounts"
        payload = {
            "username": username.strip(),
            "password": password.strip(),
            "quota": quota_mb,
            "limit": daily_limit,
        }
        logger.info("Creating MXroute mailbox: %s@%s", username, domain)
        return self._request("POST", endpoint, payload)

    def list_email_accounts(self, domain: str) -> List[Dict[str, Any]]:
        """List all mailboxes under domain."""
        endpoint = f"/domains/{domain}/email-accounts"
        res = self._request("GET", endpoint)
        return res.get("data", [])

    def delete_email_account(self, domain: str, username: str) -> bool:
        """Delete an email account."""
        endpoint = f"/domains/{domain}/email-accounts/{username}"
        self._request("DELETE", endpoint)
        logger.info("Deleted MXroute mailbox: %s@%s", username, domain)
        return True

    def get_catch_all(self, domain: str) -> Dict[str, Any]:
        """Get catch-all setting for domain."""
        return self._request("GET", f"/domains/{domain}/catch-all")

    def set_catch_all(self, domain: str, target_address: str) -> Dict[str, Any]:
        """Forward all non-existent domain addresses to target_address."""
        endpoint = f"/domains/{domain}/catch-all"
        payload = {
            "type": "address",
            "address": target_address.strip(),
        }
        logger.info("Setting catch-all for %s -> %s", domain, target_address)
        return self._request("PATCH", endpoint, payload)


class MXRouteIMAPReader:
    """Connects to MXroute IMAP over SSL to fetch Instagram OTP codes."""

    def __init__(
        self,
        email_address: str,
        password: str,
        server: str = DEFAULT_SERVER,
        port: int = DEFAULT_IMAP_PORT,
    ):
        self.email_address = email_address.strip()
        self.password = password.strip()
        self.server = server.strip()
        self.port = port
        self._imap: Optional[imaplib.IMAP4_SSL] = None

    def connect(self) -> imaplib.IMAP4_SSL:
        logger.info("Connecting to MXroute IMAP at %s:%d for %s", self.server, self.port, self.email_address)
        try:
            imap = imaplib.IMAP4_SSL(self.server, self.port)
            imap.login(self.email_address, self.password)
            self._imap = imap
            logger.info("Connected & authenticated to MXroute mailbox %s", self.email_address)
            return imap
        except Exception as e:
            logger.error("Failed to connect to MXroute IMAP: %s", e)
            raise

    def disconnect(self) -> None:
        if self._imap is not None:
            try:
                self._imap.logout()
            except Exception:
                pass
            self._imap = None

    def get_message_count(self) -> int:
        """Get total number of messages in INBOX."""
        if not self._imap:
            self.connect()
        try:
            self._imap.select("INBOX", readonly=True)
            status, data = self._imap.search(None, "ALL")
            if status == "OK" and data and data[0]:
                return len(data[0].split())
        except Exception as e:
            logger.warning("Could not get message count: %s", e)
        return 0

    def search_for_code(
        self,
        sender_filter: str = "instagram",
        min_msg_id: int = 0,
        exclude_code: str = "",
    ) -> Optional[Tuple[str, str, str]]:
        """Search INBOX for the latest email matching sender_filter and extract OTP."""
        if not self._imap:
            self.connect()

        self._imap.select("INBOX", readonly=True)
        # Search for unseen or all recent messages
        status, data = self._imap.search(None, "ALL")
        if status != "OK" or not data or not data[0]:
            return None

        msg_ids = data[0].split()
        # Look at newest emails first (last 10)
        for msg_id in reversed(msg_ids[-10:]):
            try:
                num_id = int(msg_id.decode() if isinstance(msg_id, bytes) else str(msg_id))
                if min_msg_id > 0 and num_id <= min_msg_id:
                    continue

                _, msg_data = self._imap.fetch(msg_id, "(RFC822)")
                if not msg_data or not msg_data[0]:
                    continue
                raw_msg = email.message_from_bytes(msg_data[0][1])

                sender = decode_header_val(raw_msg.get("From", ""))
                subject = decode_header_val(raw_msg.get("Subject", ""))
                body = extract_plain_text(raw_msg)
                combined_text = f"{subject}\n{body}"

                # Match sender or subject
                if sender_filter.lower() in sender.lower() or sender_filter.lower() in subject.lower():
                    match = OTP_REGEX.search(combined_text)
                    if match:
                        code = match.group(1).replace(" ", "")
                        if len(code) == 6 and code.isdigit():
                            if exclude_code and code == exclude_code:
                                continue
                            return code, sender, subject
            except Exception as e:
                logger.debug("Error checking message %s: %s", msg_id, e)
                continue

        return None

    def poll_for_otp(
        self,
        sender_filter: str = "instagram",
        timeout_seconds: int = 90,
        interval: int = 3,
        min_msg_id: int = 0,
        exclude_code: str = "",
    ) -> Optional[str]:
        logger.info(
            "Polling MXroute IMAP for Instagram OTP (max %ds, interval %ds, exclude=%s)...",
            timeout_seconds,
            interval,
            exclude_code or "none",
        )
        deadline = time.time() + timeout_seconds

        while time.time() < deadline:
            try:
                found = self.search_for_code(
                    sender_filter=sender_filter,
                    min_msg_id=min_msg_id,
                    exclude_code=exclude_code,
                )
                if found:
                    code, sender, subject = found
                    logger.info("Found OTP [%s] in email from '%s' (Subject: '%s')", code, sender, subject)
                    return code
            except Exception as e:
                logger.warning("Search attempt error: %s", e)
                self.disconnect()
                try:
                    self.connect()
                except Exception:
                    pass

            rem = int(deadline - time.time())
            if rem > 0:
                logger.info("No new code yet. Checking again in %ds... (%ds left)", interval, rem)
                time.sleep(min(interval, rem))

        logger.error("Timed out waiting for Instagram OTP in MXroute inbox.")
        return None


def fetch_mxroute_otp(
    email_address: str,
    password: str,
    server: str = DEFAULT_SERVER,
    timeout_seconds: int = 90,
    min_msg_id: int = 0,
    exclude_code: str = "",
) -> Optional[str]:
    """Helper to fetch Instagram OTP from MXroute IMAP."""
    reader = MXRouteIMAPReader(email_address=email_address, password=password, server=server)
    try:
        reader.connect()
        return reader.poll_for_otp(
            sender_filter="instagram",
            timeout_seconds=timeout_seconds,
            min_msg_id=min_msg_id,
            exclude_code=exclude_code,
        )
    finally:
        reader.disconnect()

