"""Kaggle credential discovery, verification, and configuration."""

from __future__ import annotations

import json
import os
from pathlib import Path
from typing import Any

from config import BASE_DIR

_cached_kaggle_username: str | None = None
_cached_api: Any = None
_cached_auth_fingerprint: tuple[Any, ...] | None = None


def get_kaggle_credentials() -> dict[str, Any]:
    """Detect Kaggle API credentials from environment or default file locations."""
    global _cached_kaggle_username, _cached_api, _cached_auth_fingerprint
    _cached_api = None
    _cached_auth_fingerprint = None

    # Populate unset variables from .env without overwriting credentials just
    # authenticated in this process.
    try:
        from dotenv import load_dotenv

        for candidate in [
            BASE_DIR.parent / ".env",
            BASE_DIR / ".env",
            Path.cwd() / "traintrace" / ".env",
            Path.cwd() / ".env",
        ]:
            if candidate.is_file():
                load_dotenv(candidate, override=False)
                break
    except ImportError:
        # python-dotenv is optional; process environment and Kaggle files still work.
        pass

    # 1. Check environment variables (.env loaded via config.py)
    env_token = os.getenv("KAGGLE_API_TOKEN", "").strip()
    if env_token:
        return {
            "configured": True,
            "auth_type": "token",
            "username": _cached_kaggle_username or os.getenv("KAGGLE_USERNAME", "").strip() or None,
            "token": env_token,
            "source": ".env (KAGGLE_API_TOKEN)",
        }

    env_user = os.getenv("KAGGLE_USERNAME", "").strip()
    env_key = os.getenv("KAGGLE_KEY", "").strip()
    if env_user and env_key:
        return {
            "configured": True,
            "auth_type": "key",
            "username": env_user,
            "key": env_key,
            "source": ".env (KAGGLE_USERNAME/KAGGLE_KEY)",
        }
    if env_key and not env_user:
        return {
            "configured": True,
            "auth_type": "token",
            "username": _cached_kaggle_username,
            "token": env_key,
            "source": ".env (KAGGLE_KEY)",
        }

    # 2. Check ~/.kaggle/kaggle.json (standard Kaggle token file)
    kaggle_json = Path.home() / ".kaggle" / "kaggle.json"
    if kaggle_json.is_file():
        try:
            with kaggle_json.open() as f:
                data = json.load(f)
            u = data.get("username", "").strip()
            k = data.get("key", "").strip()
            if u and k:
                return {
                    "configured": True,
                    "auth_type": "key",
                    "username": u,
                    "key": k,
                    "source": "~/.kaggle/kaggle.json",
                }
        except (OSError, json.JSONDecodeError):
            pass

    # 3. Check ~/.kaggle/access_token
    token_file = Path.home() / ".kaggle" / "access_token"
    if token_file.is_file():
        try:
            token = token_file.read_text().strip()
            if token:
                return {
                    "configured": True,
                    "auth_type": "token",
                    "username": _cached_kaggle_username,
                    "token": token,
                    "source": "~/.kaggle/access_token",
                }
        except OSError:
            pass

    return {
        "configured": False,
        "auth_type": None,
        "username": None,
        "source": None,
        "help": "Provide your Kaggle API token (KGAT_...) or Username + API key.",
    }


def resolve_kaggle_username(force: bool = False) -> str:
    """Resolve and cache real authenticated Kaggle username."""
    global _cached_kaggle_username, _cached_api, _cached_auth_fingerprint
    _cached_api = None
    _cached_auth_fingerprint = None
    if _cached_kaggle_username and not force:
        return _cached_kaggle_username

    api, username = get_authenticated_api(force=force)
    _cached_kaggle_username = username
    return username


def configure_kaggle_credentials(
    token: str | None = None,
    username: str | None = None,
    key: str | None = None,
    save_to_env: bool = True,
) -> dict[str, Any]:
    """Configure and authenticate Kaggle credentials dynamically via UI (BYOK)."""
    global _cached_kaggle_username, _cached_api, _cached_auth_fingerprint
    _cached_api = None
    _cached_auth_fingerprint = None
    token = (token or "").strip()
    username = (username or "").strip()
    key = (key or "").strip()

    if not token and not (username and key) and not key:
        raise ValueError("Please provide either a Kaggle API Token (KGAT_...) or Username + Key.")

    # Temporarily set environment variables to test authentication
    orig_token = os.environ.get("KAGGLE_API_TOKEN")
    orig_user = os.environ.get("KAGGLE_USERNAME")
    orig_key = os.environ.get("KAGGLE_KEY")

    if token:
        os.environ["KAGGLE_API_TOKEN"] = token
        os.environ.pop("KAGGLE_KEY", None)
        os.environ.pop("KAGGLE_USERNAME", None)
    elif username and key:
        os.environ["KAGGLE_USERNAME"] = username
        os.environ["KAGGLE_KEY"] = key
        os.environ.pop("KAGGLE_API_TOKEN", None)
    elif key:
        os.environ["KAGGLE_API_TOKEN"] = key
        os.environ.pop("KAGGLE_KEY", None)

    try:
        from kaggle.api.kaggle_api_extended import KaggleApi

        api = KaggleApi()
        api.authenticate()
        resolved_u = api.get_config_value("username") or username
        if not resolved_u:
            raise ValueError("Kaggle authenticated but did not return an account username")
        _cached_kaggle_username = resolved_u
    except Exception as exc:
        # Revert on failure
        if orig_token:
            os.environ["KAGGLE_API_TOKEN"] = orig_token
        else:
            os.environ.pop("KAGGLE_API_TOKEN", None)
        if orig_user:
            os.environ["KAGGLE_USERNAME"] = orig_user
        else:
            os.environ.pop("KAGGLE_USERNAME", None)
        if orig_key:
            os.environ["KAGGLE_KEY"] = orig_key
        else:
            os.environ.pop("KAGGLE_KEY", None)
        raise ValueError(f"Kaggle authentication failed: {exc}") from exc

    # Optionally persist into local .env if available
    persisted = not save_to_env
    persistence_error = None
    if save_to_env:
        try:
            env_path = (
                BASE_DIR.parent / ".env"
                if (BASE_DIR.parent / ".env").is_file()
                else BASE_DIR / ".env"
            )
            if not env_path.is_file():
                env_path = BASE_DIR / ".env"

            lines = []
            if env_path.is_file():
                lines = env_path.read_text().splitlines()

            new_lines = []
            keys_to_set = {}
            if token:
                keys_to_set["KAGGLE_API_TOKEN"] = token
            elif username and key:
                keys_to_set["KAGGLE_USERNAME"] = username
                keys_to_set["KAGGLE_KEY"] = key

            seen_keys = set()
            for line in lines:
                matched = False
                for k, v in keys_to_set.items():
                    if line.startswith(f"{k}=") or line.startswith(f"# {k}="):
                        new_lines.append(f"{k}={v}")
                        seen_keys.add(k)
                        matched = True
                        break
                if not matched:
                    new_lines.append(line)

            for k, v in keys_to_set.items():
                if k not in seen_keys:
                    new_lines.append(f"{k}={v}")

            env_path.write_text("\n".join(new_lines) + "\n")
            persisted = True
        except OSError as exc:
            persistence_error = (
                f"Credentials work for this session but could not be saved to .env: {exc}"
            )

    return {
        "configured": True,
        "username": _cached_kaggle_username,
        "persisted": persisted,
        "warning": persistence_error,
        "message": f"Successfully authenticated as Kaggle user: @{_cached_kaggle_username}",
    }


def get_authenticated_api(force: bool = False):
    """Return an authenticated KaggleApi client instance."""
    global _cached_kaggle_username, _cached_api, _cached_auth_fingerprint
    _cached_api = None
    _cached_auth_fingerprint = None, _cached_api, _cached_auth_fingerprint
    creds = get_kaggle_credentials()
    if not creds["configured"]:
        _cached_api = None
        _cached_auth_fingerprint = None
        raise ValueError(
            "Kaggle API credentials not found. Configure your Kaggle API token or Username + Key."
        )

    fingerprint = (
        creds.get("auth_type"),
        creds.get("token"),
        creds.get("username"),
        creds.get("key"),
    )
    if (
        not force
        and _cached_api is not None
        and _cached_kaggle_username
        and _cached_auth_fingerprint == fingerprint
    ):
        return _cached_api, _cached_kaggle_username

    if creds["auth_type"] == "key":
        os.environ["KAGGLE_USERNAME"] = creds["username"]
        os.environ["KAGGLE_KEY"] = creds["key"]
    elif creds["auth_type"] == "token":
        os.environ["KAGGLE_API_TOKEN"] = creds["token"]

    from kaggle.api.kaggle_api_extended import KaggleApi

    api = KaggleApi()
    api.authenticate()
    resolved_username = api.get_config_value("username") or creds.get("username")
    if not resolved_username:
        raise ValueError("Kaggle authenticated but did not return an account username")
    _cached_kaggle_username = resolved_username
    _cached_api = api
    _cached_auth_fingerprint = fingerprint
    return api, resolved_username
