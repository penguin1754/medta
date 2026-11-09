#!/usr/bin/env python3
"""Zero-quota Coze credential doctor.

Only uses read-only endpoints, so it does NOT consume chat quota:
  1. GET /v1/workspaces     -> is the PAT valid?
  2. GET /v1/bots/{bot_id}  -> does the bot exist / is it reachable with this PAT?
It prints a sha256 fingerprint of the token so you can tell whether the local
and cloud tokens are the same, without exposing the token itself.
"""
import hashlib
import json
import os
import urllib.error
import urllib.request
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent


def load_env():
    env = {}
    for f in (ROOT / ".env", ROOT / ".streamlit" / "secrets.toml"):
        if not f.exists():
            continue
        for line in f.read_text(encoding="utf-8").splitlines():
            line = line.strip()
            if not line or line.startswith("#") or "=" not in line:
                continue
            k, v = line.split("=", 1)
            env[k.strip()] = v.strip().strip('"').strip("'")
    for k in ("COZE_BASE", "COZE_BOT_ID", "COZE_PAT"):
        if os.environ.get(k):
            env[k] = os.environ[k]
    return env


def ascii_only(s):
    return str(s).encode("ascii", "replace").decode("ascii")


def get(url, token, timeout=25):
    req = urllib.request.Request(url, headers={"Authorization": "Bearer " + token}, method="GET")
    try:
        with urllib.request.urlopen(req, timeout=timeout) as r:
            return r.status, r.read().decode("utf-8", "replace")
    except urllib.error.HTTPError as e:
        return e.code, e.read().decode("utf-8", "replace")
    except Exception as e:  # noqa: BLE001
        return 0, "NETWORK %s: %s" % (type(e).__name__, str(e)[:200])


def brief(raw, limit=600):
    try:
        obj = json.loads(raw)
    except ValueError:
        return ascii_only(" ".join(raw.split())[:limit])
    if isinstance(obj, dict):
        for key in ("data", "bot", "bots"):
            if key in obj and isinstance(obj[key], (dict, list)):
                obj[key] = "<omitted>"
        obj.pop("code", None) if obj.get("code") in (0, "0") else None
    return ascii_only(json.dumps(obj, ensure_ascii=False)[:limit])


def main():
    env = load_env()
    base = (env.get("COZE_BASE") or "https://api.coze.cn").rstrip("/")
    bot_id = (env.get("COZE_BOT_ID") or "").strip()
    pat = (env.get("COZE_PAT") or "").strip()

    print("base   :", base)
    print("bot_id :", bot_id or "<empty>")
    if not pat:
        print("pat    : <empty>")
        return 2
    fp = hashlib.sha256(pat.encode("utf-8")).hexdigest()[:12]
    print("pat    : len=%d fp=%s head=%s***" % (len(pat), fp, pat[:8]))
    print("")

    for label, path in (("workspaces", "/v1/workspaces"), ("bot", "/v1/bots/" + bot_id)):
        status, raw = get(base + path, pat)
        print("[%s] %s %s" % (label, base + path, status))
        print("      " + brief(raw))
        print("")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
