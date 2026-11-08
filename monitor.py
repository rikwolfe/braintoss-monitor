#!/usr/bin/env python3
"""braintoss-monitor: uptime and TLS-expiry checks of public Braintoss URLs, alerting via ntfy.

Usage: monitor.py uptime | weekly | test

The only secret is NTFY_TOPIC (ntfy.sh topic, works as a password), taken from
the environment (GitHub Actions secret), never from files. No cloud login.
"""
import datetime as dt
import json
import os
import socket
import ssl
import sys
import time
import urllib.error
import urllib.parse
import urllib.request

import yaml

ROOT = os.path.dirname(os.path.abspath(__file__))
STATE_FILE = os.path.join(ROOT, "state", "status.json")
SITES_FILE = os.path.join(ROOT, "sites.yml")

USER_AGENT = "Mozilla/5.0 (compatible; braintoss-monitor; +https://github.com/rikwolfe/braintoss-monitor)"
TLS_WARN_DAYS = 14
RETRIES = 2


# ---------- helpers ----------

def ntfy(title, message, priority="default", tags=""):
    topic = os.environ.get("NTFY_TOPIC")
    if not topic:
        print(f"[ntfy skipped, no NTFY_TOPIC] {title}: {message}")
        return
    req = urllib.request.Request(
        "https://ntfy.sh/" + urllib.parse.quote(topic),
        data=message.encode("utf-8"),
        headers={"Title": title.encode("utf-8").decode("latin-1", "ignore"),
                 "Priority": priority, "Tags": tags},
        method="POST",
    )
    with urllib.request.urlopen(req, timeout=20) as r:
        print(f"ntfy sent ({r.status}): {title}")


def load_state(path=STATE_FILE):
    try:
        with open(path) as f:
            return json.load(f)
    except (FileNotFoundError, json.JSONDecodeError):
        return {}


def save_state(state, path=STATE_FILE):
    with open(path, "w") as f:
        json.dump(state, f, indent=2, sort_keys=True)
        f.write("\n")


def now_iso():
    return dt.datetime.now(dt.timezone.utc).replace(microsecond=0).isoformat()


# ---------- uptime ----------

def check_http(url):
    """Return (ok, detail). Follows redirects; 2xx/3xx is ok."""
    last = ""
    for attempt in range(RETRIES + 1):
        try:
            req = urllib.request.Request(url, headers={"User-Agent": USER_AGENT})
            with urllib.request.urlopen(req, timeout=20) as r:
                if 200 <= r.status < 400:
                    return True, f"HTTP {r.status}"
                last = f"HTTP {r.status}"
        except urllib.error.HTTPError as e:
            if 300 <= e.code < 400:
                return True, f"HTTP {e.code}"
            last = f"HTTP {e.code}"
        except Exception as e:  # noqa: BLE001 - any network failure counts as down
            last = type(e).__name__ + ": " + str(e)[:120]
        if attempt < RETRIES:
            time.sleep(10)
    return False, last


def cert_days_left(host):
    ctx = ssl.create_default_context()
    with socket.create_connection((host, 443), timeout=20) as sock:
        with ctx.wrap_socket(sock, server_hostname=host) as s:
            not_after = s.getpeercert()["notAfter"]
    expires = dt.datetime.fromtimestamp(ssl.cert_time_to_seconds(not_after), dt.timezone.utc)
    return (expires - dt.datetime.now(dt.timezone.utc)).days


def run_uptime():
    with open(SITES_FILE) as f:
        sites = yaml.safe_load(f)["sites"]
    state = load_state()
    sites_state = state.setdefault("sites", {})
    changed = False

    for site in sites:
        url = site["url"]
        host = urllib.parse.urlparse(url).hostname
        ok, detail = check_http(url)
        try:
            days = cert_days_left(host)
            cert_ok = days >= TLS_WARN_DAYS
        except Exception as e:  # noqa: BLE001
            days = None
            if ok:
                cert_ok, detail = False, f"TLS check failed: {type(e).__name__}"
            else:  # site is down, we already alert on that
                cert_ok = sites_state.get(url, {}).get("cert_ok", True)
        print(f"{url}: {'UP' if ok else 'DOWN'} ({detail}); cert days left: {days}")

        prev = sites_state.get(url, {})
        status = "up" if ok else "down"
        if prev.get("status") and prev["status"] != status:
            if status == "down":
                ntfy(f"DOWN: {host}", f"{url} is down: {detail}", "high", "rotating_light")
            else:
                ntfy(f"Recovered: {host}", f"{url} is back up ({detail})", "default", "white_check_mark")
        if prev.get("cert_ok", True) and not cert_ok and ok:
            ntfy(f"TLS expiring: {host}", f"Certificate for {host} expires in {days} days", "high", "lock")

        # Only write on a flip, so the state file (and git history) changes only then.
        if status != prev.get("status") or cert_ok != prev.get("cert_ok"):
            sites_state[url] = {"status": status, "cert_ok": cert_ok,
                                "detail": detail, "since": now_iso()}
            changed = True

    for gone in set(sites_state) - {s["url"] for s in sites}:
        del sites_state[gone]
        changed = True

    if changed:
        state["updated"] = now_iso()
    save_state(state)
    return changed


def run_weekly():
    state = load_state()
    sites = state.get("sites", {})
    up = sum(1 for s in sites.values() if s.get("status") == "up")
    down = [u for u, s in sites.items() if s.get("status") != "up"]
    msg = f"{up} of {len(sites)} Braintoss URLs ok" + (f"; down: {', '.join(down)}" if down else "")
    ntfy("braintoss-monitor alive", msg, "low", "heartbeat")


def main():
    cmd = sys.argv[1] if len(sys.argv) > 1 else ""
    if cmd == "uptime":
        run_uptime()
    elif cmd == "weekly":
        run_weekly()
    elif cmd == "test":
        ntfy("braintoss-monitor test", "braintoss-monitor test", "default", "test_tube")
    else:
        sys.exit(__doc__)


if __name__ == "__main__":
    main()
