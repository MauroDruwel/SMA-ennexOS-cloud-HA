#!/usr/bin/env python3
"""Retrieve current PV power from SMA ennexOS / Sunny Portal.

Uses browser-emulating PKCE OAuth2 login and calls the live power gauge API.
"""

import base64
import hashlib
import json
import os
import re
import sys
import urllib.parse
from datetime import datetime, timedelta, timezone
from typing import Optional

import requests

CLIENT_ID = "SPpbeOS"
AUTH_BASE = "https://login.sma.energy/auth/realms/SMA"
TOKEN_URL = f"{AUTH_BASE}/protocol/openid-connect/token"
AUTH_URL = f"{AUTH_BASE}/protocol/openid-connect/auth"
REDIRECT_URI = "https://ennexos.sunnyportal.com/dashboard/initialize"
API_BASE = "https://uiapi.sunnyportal.com/api/v1"

BROWSER_HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) "
        "AppleWebKit/537.36 (KHTML, like Gecko) "
        "Chrome/150.0.0.0 Safari/537.36"
    ),
    "Accept-Language": "en-US,en;q=0.9",
    "sec-ch-ua": '"Not;A=Brand";v="8", "Chromium";v="150", "Google Chrome";v="150"',
    "sec-ch-ua-mobile": "?0",
    "sec-ch-ua-platform": '"macOS"',
}


def _b64_encode(data: bytes) -> str:
    return base64.urlsafe_b64encode(data).rstrip(b"=").decode()


def _generate_pkce() -> tuple[str, str]:
    verifier = _b64_encode(os.urandom(32))
    challenge = _b64_encode(hashlib.sha256(verifier.encode()).digest())
    return verifier, challenge


def _random_str() -> str:
    return _b64_encode(os.urandom(32))


class SmaSession:
    def __init__(self, username: str, password: str):
        self.username = username
        self.password = password
        self._http = requests.Session()
        self._http.headers.update(BROWSER_HEADERS)
        self.access_token: Optional[str] = None
        self.refresh_token: Optional[str] = None
        self.component_id: Optional[str] = None

    # ── Auth ──────────────────────────────────────────────────────────

    def login(self) -> None:
        code_verifier, code_challenge = _generate_pkce()
        state = _random_str()
        nonce = _random_str()

        # 1. GET the auth page – we need the session cookies + form action
        params = {
            "response_type": "code",
            "client_id": CLIENT_ID,
            "redirect_uri": REDIRECT_URI,
            "scope": "openid profile",
            "state": state,
            "code_challenge": code_challenge,
            "code_challenge_method": "S256",
            "nonce": nonce,
        }
        r = self._http.get(
            AUTH_URL,
            params=params,
            headers={
                "Accept": (
                    "text/html,application/xhtml+xml,application/xml;"
                    "q=0.9,image/avif,image/webp,image/apng,*/*;q=0.8"
                ),
                "Sec-Fetch-Dest": "document",
                "Sec-Fetch-Mode": "navigate",
                "Sec-Fetch-Site": "cross-site",
                "Upgrade-Insecure-Requests": "1",
            },
        )
        r.raise_for_status()

        # 2. Parse the login form to extract the action URL
        form_action = self._parse_form_action(r.text)
        if not form_action:
            raise RuntimeError("Could not find login form in the auth page")

        # 3. POST credentials to the form action
        form_url = urllib.parse.urljoin(AUTH_URL, form_action)
        r2 = self._http.post(
            form_url,
            data={
                "username": self.username,
                "password": self.password,
                "credentialId": "",
            },
            headers={
                "Content-Type": "application/x-www-form-urlencoded",
                "Origin": "null",
                "Sec-Fetch-Dest": "document",
                "Sec-Fetch-Mode": "navigate",
                "Sec-Fetch-Site": "same-origin",
                "Upgrade-Insecure-Requests": "1",
            },
            allow_redirects=False,
        )
        r2.raise_for_status()

        # 4. Follow the redirect to grab the auth code
        location = r2.headers.get("Location")
        if not location:
            raise RuntimeError("No redirect after login – check credentials")
        parsed = urllib.parse.urlparse(location)
        qs = urllib.parse.parse_qs(parsed.query)
        auth_code = qs.get("code", [None])[0]
        if not auth_code:
            raise RuntimeError(
                f"No auth code in redirect URL: {location}"
            )

        # 5. Exchange auth code for tokens
        r3 = self._http.post(
            TOKEN_URL,
            data={
                "grant_type": "authorization_code",
                "code": auth_code,
                "redirect_uri": REDIRECT_URI,
                "code_verifier": code_verifier,
                "client_id": CLIENT_ID,
            },
            headers={
                "Content-Type": "application/x-www-form-urlencoded",
                "Origin": "https://ennexos.sunnyportal.com",
                "Referer": "https://ennexos.sunnyportal.com/",
                "Sec-Fetch-Dest": "empty",
                "Sec-Fetch-Mode": "cors",
                "Sec-Fetch-Site": "cross-site",
            },
        )
        r3.raise_for_status()
        token_data = r3.json()
        self.access_token = token_data["access_token"]
        self.refresh_token = token_data.get("refresh_token")

    def refresh_access_token(self) -> None:
        if not self.refresh_token:
            raise RuntimeError("No refresh token available – login again")
        r = self._http.post(
            TOKEN_URL,
            data={
                "grant_type": "refresh_token",
                "refresh_token": self.refresh_token,
                "client_id": CLIENT_ID,
            },
            headers={
                "Content-Type": "application/x-www-form-urlencoded",
                "Origin": "https://ennexos.sunnyportal.com",
                "Referer": "https://ennexos.sunnyportal.com/",
                "Sec-Fetch-Dest": "empty",
                "Sec-Fetch-Mode": "cors",
                "Sec-Fetch-Site": "cross-site",
            },
        )
        r.raise_for_status()
        token_data = r.json()
        self.access_token = token_data["access_token"]
        if "refresh_token" in token_data:
            self.refresh_token = token_data["refresh_token"]

    @staticmethod
    def _parse_form_action(html: str) -> Optional[str]:
        m = re.search(
            r'<form[^>]*\saction=["\']([^"\']+)["\']',
            html,
            re.IGNORECASE,
        )
        if m:
            return m.group(1)
        return None

    # ── API helpers ───────────────────────────────────────────────────

    def _api_headers(self) -> dict:
        if not self.access_token:
            raise RuntimeError("Not logged in")
        return {
            "Authorization": f"Bearer {self.access_token}",
            "Accept": "application/json, text/plain, */*",
            "Origin": "https://ennexos.sunnyportal.com",
            "Referer": "https://ennexos.sunnyportal.com/",
            "Sec-Fetch-Dest": "empty",
            "Sec-Fetch-Mode": "cors",
            "Sec-Fetch-Site": "same-site",
        }

    def _api_get(self, path: str, **kwargs) -> requests.Response:
        r = self._http.get(
            f"{API_BASE}{path}",
            headers=self._api_headers(),
            **kwargs,
        )
        if r.status_code == 401:
            self.refresh_access_token()
            r = self._http.get(
                f"{API_BASE}{path}",
                headers=self._api_headers(),
                **kwargs,
            )
        r.raise_for_status()
        return r

    def _api_post(self, path: str, json_body: dict) -> requests.Response:
        r = self._http.post(
            f"{API_BASE}{path}",
            json=json_body,
            headers={**self._api_headers(), "Content-Type": "application/json"},
        )
        if r.status_code == 401:
            self.refresh_access_token()
            r = self._http.post(
                f"{API_BASE}{path}",
                json=json_body,
                headers={**self._api_headers(), "Content-Type": "application/json"},
            )
        r.raise_for_status()
        return r

    # ── Discover component / plant ───────────────────────────────────

    def discover_plant(self) -> str:
        nav = self._api_get("/navigation").json()
        plant_id = nav[0]["componentId"] if isinstance(nav, list) else nav["componentId"]
        self.component_id = str(plant_id)
        return self.component_id

    # ── Power data ────────────────────────────────────────────────────

    def get_current_power(self) -> dict:
        if not self.component_id:
            self.discover_plant()
        r = self._api_get(
            f"/widgets/gauge/power",
            params={
                "componentId": self.component_id,
                "type": "PvProduction",
            },
        )
        return r.json()

    def get_plant_name(self) -> str:
        if not self.component_id:
            self.discover_plant()
        r = self._api_get(f"/plants/{self.component_id}")
        return r.json().get("name", str(self.component_id))

    def get_device_status(self) -> dict:
        if not self.component_id:
            self.discover_plant()
        r = self._api_get(f"/components/{self.component_id}/livestatus")
        return r.json()

    def get_daily_energy(self) -> dict:
        if not self.component_id:
            self.discover_plant()
        now = datetime.now(timezone.utc)
        prev = now - timedelta(days=1)
        r = self._api_post(
            "/measurements/search",
            {
                "queryItems": [
                    {
                        "componentId": self.component_id,
                        "channelId": "Measurement.Metering.TotWhOut.Pv",
                        "resolution": "OneDay",
                        "timezone": "Europe/Brussels",
                        "aggregate": "Dif",
                        "multiAggregate": "Sum",
                    }
                ],
                "dateTimeBegin": prev.strftime("%Y-%m-%dT22:00:00.000Z"),
                "dateTimeEnd": now.strftime("%Y-%m-%dT22:00:00.000Z"),
            },
        )
        data = r.json()
        for channel in data:
            if channel["channelId"] == "Measurement.Metering.TotWhOut.Pv":
                for v in channel.get("values", []):
                    if v.get("value") is not None:
                        return {
                            "wh": v["value"],
                            "timestamp": v["time"],
                            "min": channel.get("min"),
                            "max": channel.get("max"),
                        }
        return {"wh": 0}


# ── CLI ───────────────────────────────────────────────────────────────

POLL_INTERVAL = 5      # seconds – power gauge (matches website)
ENERGY_INTERVAL = 30   # seconds – daily energy (slow-changing meter value)


def main():
    import argparse
    import time

    parser = argparse.ArgumentParser(
        description="Poll PV power from SMA ennexOS / Sunny Portal (5s interval like the website)"
    )
    parser.add_argument("username", help="SMA ID / Sunny Portal email")
    parser.add_argument("password", help="SMA ID password")
    parser.add_argument(
        "--component",
        help="Component / plant ID (auto-discovered if omitted)",
    )
    parser.add_argument(
        "--once",
        action="store_true",
        help="Fetch once and exit instead of polling",
    )
    args = parser.parse_args()

    sma = SmaSession(args.username, args.password)
    if args.component:
        sma.component_id = args.component

    print("Logging in ...", file=sys.stderr)
    sma.login()
    print("Discovering plant ...", file=sys.stderr)
    plant_name = sma.get_plant_name()
    print(f"Plant: {plant_name}", file=sys.stderr)

    energy = sma.get_daily_energy()
    daily_wh = energy["wh"]
    last_energy_poll = 0.0

    try:
        while True:
            now = time.monotonic()
            try:
                power = sma.get_current_power()

                if now - last_energy_poll >= ENERGY_INTERVAL:
                    energy = sma.get_daily_energy()
                    daily_wh = energy["wh"]
                    last_energy_poll = now

                output = {
                    "watts": power["value"],
                    "daily_wh": daily_wh,
                    "plant": plant_name,
                    "ts": power.get("timestamp", ""),
                }
                json.dump(output, sys.stdout)
                print()
                sys.stdout.flush()

                if args.once:
                    break

            except Exception as e:
                print(f'{{"error": {json.dumps(str(e))}}}', file=sys.stderr)
                if args.once:
                    raise

            time.sleep(POLL_INTERVAL)
    except KeyboardInterrupt:
        pass


if __name__ == "__main__":
    main()
