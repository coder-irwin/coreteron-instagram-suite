#!/usr/bin/env python3
"""SMSPool API Client for Instagram Verification.

Handles:
1. Balance checks and account validation
2. Temporary phone number purchasing for Instagram
3. Polling and extracting incoming SMS OTP verification codes
4. Order cancellation and automated refunds
API Documentation: https://api.smspool.net
"""

from __future__ import annotations

import json
import logging
import os
import re
import time
from typing import Any, Callable, Dict, List, Optional
import urllib.error
import urllib.parse
import urllib.request

logger = logging.getLogger("smspool_client")

API_BASE_URL = "https://api.smspool.net"
DEFAULT_COUNTRY = "CA"
DEFAULT_SERVICE = "457"
OTP_REGEX = re.compile(r"(?<!\d)(\d{6})(?!\d)")


class SMSPoolError(Exception):
    """Custom exception for SMSPool API errors."""
    pass


class SMSPoolClient:
    """Production client for SMSPool (smspool.net) REST API."""

    def __init__(self, api_key: Optional[str] = None):
        self.api_key = (api_key or os.getenv("SMSPOOL_API_KEY", "")).strip()

    def _make_request(
        self,
        endpoint: str,
        data: Optional[Dict[str, Any]] = None,
        method: str = "POST",
        timeout: int = 20,
    ) -> Dict[str, Any]:
        """Make an authenticated HTTP request to SMSPool API."""
        url = f"{API_BASE_URL.rstrip('/')}/{endpoint.lstrip('/')}"
        payload = dict(data or {})
        
        # Inject API key if available
        if self.api_key and "key" not in payload:
            payload["key"] = self.api_key

        headers = {
            "User-Agent": "Coreteron-Instagram-Suite/2.0",
            "Accept": "application/json",
        }
        if self.api_key:
            headers["Authorization"] = f"Bearer {self.api_key}"

        encoded_data = None
        if method.upper() == "POST":
            headers["Content-Type"] = "application/x-www-form-urlencoded"
            encoded_data = urllib.parse.urlencode(payload).encode("utf-8")
        elif payload:
            query = urllib.parse.urlencode(payload)
            url = f"{url}?{query}"

        req = urllib.request.Request(url, data=encoded_data, headers=headers, method=method.upper())
        try:
            with urllib.request.urlopen(req, timeout=timeout) as resp:
                raw = resp.read().decode("utf-8", errors="replace")
                try:
                    return json.loads(raw)
                except json.JSONDecodeError:
                    return {"success": 0, "message": raw}
        except urllib.error.HTTPError as he:
            err_body = he.read().decode("utf-8", errors="replace")
            logger.error("SMSPool HTTP error %s (%s): %s", he.code, url, err_body)
            try:
                parsed = json.loads(err_body)
                return parsed
            except Exception:
                return {"success": 0, "message": f"HTTP {he.code}: {err_body}"}
        except Exception as e:
            logger.error("SMSPool connection error: %s", e)
            return {"success": 0, "message": str(e)}

    def check_balance(self) -> Dict[str, Any]:
        """Check current wallet balance on SMSPool."""
        if not self.api_key:
            return {"success": False, "message": "SMSPool API Key is not configured."}

        res = self._make_request("request/balance", data={"key": self.api_key}, method="POST")
        if "balance" in res:
            try:
                bal = float(res["balance"])
                return {"success": True, "balance": bal, "currency": "USD"}
            except (ValueError, TypeError):
                return {"success": True, "balance": res["balance"], "currency": "USD"}

        msg = res.get("message") or res.get("error") or "Unknown error retrieving balance."
        return {"success": False, "message": msg}

    def retrieve_countries(self) -> List[Dict[str, Any]]:
        """Fetch list of supported countries from SMSPool."""
        res = self._make_request("country/retrieve_all", method="GET")
        if isinstance(res, list):
            return res
        return []

    def retrieve_services(self) -> List[Dict[str, Any]]:
        """Fetch list of supported services from SMSPool."""
        res = self._make_request("service/retrieve_all", method="GET")
        if isinstance(res, list):
            return res
        return []

    def purchase_sms(
        self,
        country: str = DEFAULT_COUNTRY,
        service: str = DEFAULT_SERVICE,
        pool: Optional[int] = None,
        max_price: Optional[float] = None,
    ) -> Dict[str, Any]:
        """Purchase a temporary phone number for SMS verification.
        
        Returns:
            Dict containing order_id, phonenumber, cc, full_number, and expiration info.
        """
        if not self.api_key:
            return {"success": False, "message": "SMSPool API Key is required."}

        data: Dict[str, Any] = {
            "key": self.api_key,
            "country": country,
            "service": service,
        }
        if pool is not None:
            data["pool"] = pool
        if max_price is not None:
            data["maxPrice"] = max_price

        res = self._make_request("purchase/sms", data=data, method="POST")

        # SMSPool returns success: 1 on success
        success_val = res.get("success")
        if success_val == 1 or str(success_val) == "1":
            order_id = str(res.get("order_id", ""))
            cc = str(res.get("cc", "")).lstrip("+")
            raw_phone = str(res.get("phonenumber") or res.get("number") or "")
            
            # Build international format
            if raw_phone.startswith("+"):
                full_phone = raw_phone
            elif cc and not raw_phone.startswith(cc):
                full_phone = f"+{cc}{raw_phone}"
            else:
                full_phone = f"+{raw_phone}"

            return {
                "success": True,
                "order_id": order_id,
                "cc": cc,
                "phonenumber": raw_phone,
                "full_number": full_phone,
                "country": res.get("country", country),
                "service": res.get("service", service),
                "expires_in": res.get("expires_in", 600),
                "message": res.get("message", "Number acquired successfully."),
            }

        msg = res.get("message") or res.get("error") or "Failed to purchase phone number from SMSPool."
        return {"success": False, "message": msg}

    def check_sms(self, order_id: str) -> Dict[str, Any]:
        """Check status of an active SMS order.
        
        Status codes:
            1: Pending (waiting for code)
            2: Expired
            3: Completed (code received)
            5: Cancelled
            6: Refunded
        """
        if not self.api_key:
            return {"success": False, "message": "SMSPool API Key is required."}

        res = self._make_request("sms/check", data={"key": self.api_key, "orderid": order_id}, method="POST")
        
        status = res.get("status")
        sms_code = res.get("sms")
        full_sms = res.get("full_sms", "")

        # Try to parse 6-digit code if 'sms' is empty but 'full_sms' exists
        if not sms_code and full_sms:
            match = OTP_REGEX.search(full_sms)
            if match:
                sms_code = match.group(1)

        return {
            "success": True if status == 3 else False,
            "status": status,
            "status_text": self._status_to_text(status),
            "sms": sms_code or "",
            "full_sms": full_sms,
            "time_left": res.get("time_left", 0),
            "raw": res,
        }

    def cancel_sms(self, order_id: str) -> Dict[str, Any]:
        """Cancel an SMS order to trigger a refund."""
        if not self.api_key:
            return {"success": False, "message": "SMSPool API Key is required."}

        res = self._make_request("sms/cancel", data={"key": self.api_key, "orderid": order_id}, method="POST")
        success_val = res.get("success")
        is_success = bool(success_val == 1 or str(success_val) == "1")
        msg = res.get("message", "Order cancelled and refunded." if is_success else "Could not cancel order.")
        return {"success": is_success, "message": msg}

    def wait_for_sms_otp(
        self,
        order_id: str,
        timeout_seconds: int = 300,
        poll_interval: float = 3.5,
        callback: Optional[Callable[[str, Dict[str, Any]], None]] = None,
    ) -> Optional[str]:
        """Poll SMSPool until the SMS verification code arrives or timeout occurs."""
        deadline = time.time() + timeout_seconds
        logger.info("Awaiting SMS code for order %s (timeout: %ss)...", order_id, timeout_seconds)

        while time.time() < deadline:
            res = self.check_sms(order_id)
            status = res.get("status")
            sms = res.get("sms")

            if callback:
                try:
                    callback(res.get("status_text", "Pending"), res)
                except Exception:
                    pass

            # Completed: code arrived
            if status == 3 and sms:
                logger.info("SMS code received for order %s: %s", order_id, sms)
                return str(sms).strip()

            # Terminal states: Expired, Cancelled, Refunded
            if status in (2, 5, 6):
                logger.warning("Order %s terminated with status %s", order_id, status)
                return None

            time.sleep(poll_interval)

        logger.warning("Timed out waiting for SMS code for order %s after %ss", order_id, timeout_seconds)
        # Attempt cancellation on timeout to reclaim balance
        try:
            self.cancel_sms(order_id)
        except Exception:
            pass
        return None

    @staticmethod
    def _status_to_text(status: Optional[int]) -> str:
        status_map = {
            1: "Pending",
            2: "Expired",
            3: "Completed",
            4: "Resend Requested",
            5: "Cancelled",
            6: "Refunded",
            7: "Processing",
            8: "Activating",
        }
        return status_map.get(status, f"Unknown ({status})")
