"""Opt-in Google read smoke test through an isolated local AURA API."""
import argparse
from datetime import datetime, timedelta, timezone
from getpass import getpass
from urllib.parse import parse_qs, urlsplit
import warnings
import webbrowser

import httpx


SCOPES = {"gmail": "gmail.readonly", "calendar": "calendar.freebusy", "drive": "drive.readonly"}
PREFIX = "https://www.googleapis.com/auth/"
ROOT = "http://127.0.0.1:8000/api/integrations/google"


def checked_json(response, step):
    if response.status_code != 200:
        raise RuntimeError(f"{step} returned HTTP {response.status_code}.")
    payload = response.json()
    if not isinstance(payload, dict):
        raise RuntimeError(f"{step} returned an invalid response.")
    return payload


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("service", choices=SCOPES)
    args = parser.parse_args()
    try:
        if input("After explicit approval, type APPROVE to use the dedicated Google test account: ") != "APPROVE":
            print("BLOCKED. Approval was not supplied.")
            return 2
        with warnings.catch_warnings():
            warnings.simplefilter("error")
            token = getpass("Dedicated local AURA test user's bearer token: ").strip()
        if not token:
            raise RuntimeError("An AURA test bearer token is required.")
        with httpx.Client(base_url=ROOT, headers={"Authorization": f"Bearer {token}"},
                          timeout=20, trust_env=False, follow_redirects=False) as client:
            if checked_json(client.get("status"), "Local status").get("status") != "disconnected":
                raise RuntimeError("Use a disconnected local test user for each service.")
            authorization = checked_json(client.get("connect", params={"service": args.service}), "Connect")
            url = authorization.get("authorization_url", "")
            target = urlsplit(url)
            if (target.scheme, target.netloc, target.path) != (
                "https", "accounts.google.com", "/o/oauth2/v2/auth",
            ):
                raise RuntimeError("Unexpected Google authorization endpoint.")
            expected = {"openid", PREFIX + "userinfo.email", PREFIX + SCOPES[args.service]}
            query = parse_qs(target.query)
            if set(query.get("scope", [""])[0].split()) != expected or not query.get("state"):
                raise RuntimeError("Authorization URL did not match the selected read service.")
            if not webbrowser.open(url):
                raise RuntimeError("Could not open the Google consent screen.")
            if input("Confirm the dedicated account completed consent. Type READ to continue: ") != "READ":
                print("BLOCKED. Read approval was not supplied.")
                return 2
            status = checked_json(client.get("status"), "Local status")
            if status.get("status") != "connected" or set(status.get("scopes", [])) != expected:
                raise RuntimeError("Connected scopes did not match the selected read service.")
            body = {"service": args.service, "authorized": True}
            if args.service == "calendar":
                now = datetime.now(timezone.utc)
                body.update(start_at=now.isoformat(), end_at=(now + timedelta(days=1)).isoformat())
            result = checked_json(client.post("read", json=body), "Provider read")
            if args.service != "calendar" and result.get("nextPageToken"):
                body["page_token"] = result["nextPageToken"]
                checked_json(client.post("read", json=body), "Next page")
                print("PASS. Pagination followed one continuation.")
    except RuntimeError as exc:
        print(f"BLOCKED. {exc}")
        return 1
    except (ValueError, TypeError, httpx.HTTPError, Warning, EOFError, KeyboardInterrupt):
        print("BLOCKED. Smoke test did not complete.")
        return 1
    print(f"PASS. {args.service} read with the selected read-only scope.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
