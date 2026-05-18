from __future__ import annotations

from dataclasses import dataclass
import os

from dotenv import load_dotenv


@dataclass(frozen=True)
class Settings:
    username: str
    password: str
    base_url: str = "https://api.rinaacc.com.br"


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
    )

