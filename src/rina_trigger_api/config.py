from __future__ import annotations

from dataclasses import dataclass
import os

from dotenv import load_dotenv


@dataclass(frozen=True)
class Settings:
    username: str
    password: str
    base_url: str = "https://api.rinaacc.com.br"
    rate_limit_requests: int = 30
    rate_limit_window_seconds: int = 60


def load_settings() -> Settings:
    load_dotenv()
    username = os.getenv("USERNAME")
    password = os.getenv("PASSWORD")
    missing = [key for key, value in {"USERNAME": username, "PASSWORD": password}.items() if not value]
    if missing:
        raise RuntimeError(f"Missing required environment variable(s): {', '.join(missing)}")
    return Settings(
        username=username or "",
        password=password or "",
        base_url=os.getenv("RINA_BASE_URL", "https://api.rinaacc.com.br"),
        rate_limit_requests=positive_int_env("RATE_LIMIT_REQUESTS", 30),
        rate_limit_window_seconds=positive_int_env("RATE_LIMIT_WINDOW_SECONDS", 60),
    )


def positive_int_env(name: str, default: int) -> int:
    raw_value = os.getenv(name)
    if raw_value is None:
        return default
    try:
        value = int(raw_value)
    except ValueError as exc:
        raise RuntimeError(f"{name} must be a positive integer.") from exc
    if value <= 0:
        raise RuntimeError(f"{name} must be a positive integer.")
    return value
