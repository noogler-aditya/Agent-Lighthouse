from __future__ import annotations

import argparse
import getpass
import json
import os
import re
import sys
from pathlib import Path
from typing import Any

import httpx

DEFAULT_BASE_URL = "https://agent-lighthouse.onrender.com"
ENV_KEYS = ("LIGHTHOUSE_API_KEY", "LIGHTHOUSE_BASE_URL")


def _find_project_root(start: Path | None = None) -> Path:
    start = start or Path.cwd()
    for candidate in [start, *start.parents]:
        if (candidate / "pyproject.toml").exists():
            return candidate
        if (candidate / "requirements.txt").exists():
            return candidate
        if (candidate / ".git").exists():
            return candidate
    return start


def _load_env(env_path: Path) -> dict[str, str]:
    env: dict[str, str] = {}
    if not env_path.exists():
        return env
    for line in env_path.read_text().splitlines():
        stripped = line.strip()
        if not stripped or stripped.startswith("#"):
            continue
        if "=" not in stripped:
            continue
        key, value = stripped.split("=", 1)
        env[key.strip()] = value.strip().strip('"').strip("'")
    return env


_ENV_LINE_RE = re.compile(r"^\s*([A-Za-z_][A-Za-z0-9_]*)\s*=")


def _upsert_env(env_path: Path, updates: dict[str, str]) -> None:
    lines: list[str] = []
    if env_path.exists():
        lines = env_path.read_text().splitlines()

    key_to_index: dict[str, int] = {}
    for idx, line in enumerate(lines):
        match = _ENV_LINE_RE.match(line)
        if match:
            key_to_index[match.group(1)] = idx

    for key, value in updates.items():
        line_value = f"{key}={value}"
        if key in key_to_index:
            lines[key_to_index[key]] = line_value
        else:
            lines.append(line_value)

    env_path.write_text("\n".join(lines).rstrip() + "\n")


def _request_json(
    method: str,
    url: str,
    *,
    headers: dict[str, str] | None = None,
    json_payload: dict[str, Any] | None = None,
    params: dict[str, Any] | None = None,
) -> httpx.Response:
    with httpx.Client(timeout=10.0) as client:
        return client.request(method, url, headers=headers, json=json_payload, params=params)


def _print_json(payload: Any) -> None:
    print(json.dumps(payload, indent=2, sort_keys=True))


def _format_status_payload(base_url: str, health: dict[str, Any], auth: dict[str, Any]) -> dict[str, Any]:
    return {
        "base_url": base_url,
        "health": health,
        "auth": auth,
    }


def _resolve_base_url(env: dict[str, str]) -> str:
    return env.get("LIGHTHOUSE_BASE_URL") or os.getenv("LIGHTHOUSE_BASE_URL") or DEFAULT_BASE_URL


def _command_init(_args: argparse.Namespace) -> int:
    root = _find_project_root()
    env_path = root / ".env"
    env = _load_env(env_path)
    default_base_url = env.get("LIGHTHOUSE_BASE_URL") or DEFAULT_BASE_URL

    prompt = f"Base URL [{default_base_url}]: "
    base_url_input = input(prompt).strip()
    base_url = base_url_input or default_base_url

    username = input("Username: ").strip()
    if not username:
        print("Username is required.")
        return 1
    password = getpass.getpass("Password: ").strip()
    if not password:
        print("Password is required.")
        return 1

    login_url = f"{base_url.rstrip('/')}/api/auth/login"
    login_resp = _request_json("POST", login_url, json_payload={"username": username, "password": password})
    if login_resp.status_code != 200:
        print(f"Login failed ({login_resp.status_code}).")
        try:
            print(login_resp.json().get("detail", login_resp.text))
        except Exception:
            print(login_resp.text)
        return 1

    token = login_resp.json().get("access_token")
    if not token:
        print("Login response missing access_token.")
        return 1

    api_key_url = f"{base_url.rstrip('/')}/api/auth/api-key"
    api_key_resp = _request_json(
        "GET",
        api_key_url,
        headers={"Authorization": f"Bearer {token}"},
    )
    if api_key_resp.status_code != 200:
        print(f"API key fetch failed ({api_key_resp.status_code}).")
        try:
            print(api_key_resp.json().get("detail", api_key_resp.text))
        except Exception:
            print(api_key_resp.text)
        return 1

    api_key = api_key_resp.json().get("api_key")
    if not api_key:
        print("API key response missing api_key.")
        return 1

    _upsert_env(env_path, {"LIGHTHOUSE_API_KEY": api_key, "LIGHTHOUSE_BASE_URL": base_url})
    print(f"Updated {env_path} with LIGHTHOUSE_API_KEY and LIGHTHOUSE_BASE_URL.")
    return 0


def _command_status(args: argparse.Namespace) -> int:
    root = _find_project_root()
    env = _load_env(root / ".env")
    base_url = _resolve_base_url(env)
    health_url = f"{base_url.rstrip('/')}/health"

    try:
        health_resp = _request_json("GET", health_url)
    except httpx.RequestError as exc:
        payload = _format_status_payload(base_url, {"ok": False, "error": str(exc)}, {"ok": False})
        if args.json:
            _print_json(payload)
        else:
            print(f"Base URL: {base_url}")
            print(f"Health: error ({exc})")
            print("Auth: not checked")
        return 1

    health_payload = {"ok": health_resp.status_code == 200}
    if health_resp.status_code == 200:
        try:
            health_payload = health_resp.json()
        except Exception:
            health_payload = {"ok": False, "error": "Invalid JSON from /health"}
    else:
        health_payload["error"] = health_resp.text

    api_key = env.get("LIGHTHOUSE_API_KEY") or os.getenv("LIGHTHOUSE_API_KEY")
    auth_payload: dict[str, Any] = {"ok": False}
    if api_key:
        auth_resp = _request_json(
            "GET",
            f"{base_url.rstrip('/')}/api/auth/me",
            headers={
                "Authorization": f"Bearer {api_key}",
                "X-API-Key": api_key,
            },
        )
        if auth_resp.status_code == 200:
            auth_payload = {"ok": True, **auth_resp.json()}
        else:
            auth_payload = {"ok": False, "status_code": auth_resp.status_code}
    else:
        auth_payload = {"ok": False, "error": "LIGHTHOUSE_API_KEY not set"}

    payload = _format_status_payload(base_url, health_payload, auth_payload)
    if args.json:
        _print_json(payload)
        return 0

    print(f"Base URL: {base_url}")
    status_value = health_payload.get("status") or ("ok" if health_payload.get("ok") else "error")
    print(f"Health: {status_value}")
    auth_ok = "ok" if auth_payload.get("ok") else "failed"
    print(f"Auth: {auth_ok}")
    return 0 if health_payload.get("ok") else 1


def _command_traces(args: argparse.Namespace) -> int:
    root = _find_project_root()
    env = _load_env(root / ".env")
    base_url = _resolve_base_url(env)
    api_key = env.get("LIGHTHOUSE_API_KEY") or os.getenv("LIGHTHOUSE_API_KEY")

    if not api_key:
        print("LIGHTHOUSE_API_KEY not set. Run `agent-lighthouse init` first.")
        return 1

    traces_url = f"{base_url.rstrip('/')}/api/traces"
    resp = _request_json(
        "GET",
        traces_url,
        headers={"X-API-Key": api_key},
        params={"limit": max(1, args.last)},
    )
    if resp.status_code != 200:
        print(f"Trace list failed ({resp.status_code}).")
        print(resp.text)
        return 1

    payload = resp.json()
    traces = payload.get("traces", [])

    if args.json:
        result = [
            {
                "trace_id": t.get("trace_id"),
                "name": t.get("name"),
                "status": t.get("status"),
                "created_at": t.get("start_time"),
                "cost_usd": t.get("total_cost_usd"),
            }
            for t in traces
        ]
        _print_json(result)
        return 0

    if not traces:
        print("No traces found.")
        return 0

    print(f"Showing last {len(traces)} traces:")
    for trace in traces:
        trace_id = trace.get("trace_id", "-")
        name = trace.get("name", "-")
        status = trace.get("status", "-")
        created_at = trace.get("start_time", "-")
        cost = trace.get("total_cost_usd", 0.0)
        print(f"- {trace_id} | {name} | {status} | {created_at} | ${cost:.4f}")
    return 0


def main() -> None:
    parser = argparse.ArgumentParser(prog="agent-lighthouse", description="Agent Lighthouse CLI")
    subparsers = parser.add_subparsers(dest="command")

    init_parser = subparsers.add_parser("init", help="Authenticate and write .env")
    init_parser.set_defaults(func=_command_init)

    status_parser = subparsers.add_parser("status", help="Check backend health and auth status")
    status_parser.add_argument("--json", action="store_true", help="Output JSON")
    status_parser.set_defaults(func=_command_status)

    traces_parser = subparsers.add_parser("traces", help="List recent traces")
    traces_parser.add_argument("--last", type=int, default=5, help="Number of traces to show")
    traces_parser.add_argument("--json", action="store_true", help="Output JSON")
    traces_parser.set_defaults(func=_command_traces)

    args = parser.parse_args()
    if not hasattr(args, "func"):
        parser.print_help()
        sys.exit(1)
    sys.exit(args.func(args))
