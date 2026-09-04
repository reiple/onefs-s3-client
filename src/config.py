from __future__ import annotations

import json
import sys
from dataclasses import dataclass
from pathlib import Path
from typing import Any


@dataclass(frozen=True)
class AppConfig:
    endpoint_url: str
    access_key: str
    secret_key: str
    region_name: str
    bucket_name: str
    verify_ssl: bool
    ca_bundle: str
    s3_addressing_style: str

    @property
    def verify_parameter(self) -> bool | str:
        if not self.verify_ssl:
            return False
        return self.ca_bundle or True


def application_base_dir() -> Path:
    if getattr(sys, "frozen", False):
        return Path(sys.executable).resolve().parent
    return Path(__file__).resolve().parent.parent


def default_config_path() -> Path:
    return application_base_dir() / "config.json"


def mask_secret(value: str) -> str:
    if len(value) <= 8:
        return "*" * len(value)
    return f"{value[:4]}********{value[-4:]}"


def load_config(path: Path | None = None) -> AppConfig:
    config_path = path or default_config_path()
    if not config_path.exists():
        raise FileNotFoundError(f"Config file not found: {config_path}")

    try:
        data = json.loads(config_path.read_text(encoding="utf-8"))
    except json.JSONDecodeError as exc:
        raise ValueError(f"Invalid JSON config: {config_path}: {exc}") from exc

    required = ["endpoint_url", "access_key", "secret_key", "bucket_name"]
    missing = [name for name in required if not data.get(name)]
    if missing:
        raise ValueError(f"Missing required config field(s): {', '.join(missing)}")

    return AppConfig(
        endpoint_url=str(data["endpoint_url"]).rstrip("/"),
        access_key=str(data["access_key"]),
        secret_key=str(data["secret_key"]),
        region_name=str(data.get("region_name") or "us-east-1"),
        bucket_name=str(data["bucket_name"]),
        verify_ssl=bool(data.get("verify_ssl", True)),
        ca_bundle=str(data.get("ca_bundle") or ""),
        s3_addressing_style=str(data.get("s3_addressing_style") or "path"),
    )


def safe_config_for_log(config: AppConfig) -> dict[str, Any]:
    return {
        "endpoint_url": config.endpoint_url,
        "access_key": mask_secret(config.access_key),
        "region_name": config.region_name,
        "bucket_name": config.bucket_name,
        "verify_ssl": config.verify_ssl,
        "ca_bundle": config.ca_bundle,
        "s3_addressing_style": config.s3_addressing_style,
    }
