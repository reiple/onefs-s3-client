from __future__ import annotations

import logging
import re
from datetime import datetime
from pathlib import Path


SENSITIVE_PATTERNS = [
    re.compile(r"(secret_key\s*[=:]\s*)\S+", re.IGNORECASE),
    re.compile(r"(Authorization\s*:\s*)[^\r\n]+", re.IGNORECASE),
    re.compile(r"(AWS4-HMAC-SHA256\s+)[^\r\n]+", re.IGNORECASE),
    re.compile(r"(Signature=)[0-9a-fA-F]+", re.IGNORECASE),
]


class SecretFilter(logging.Filter):
    def filter(self, record: logging.LogRecord) -> bool:
        message = record.getMessage()
        for pattern in SENSITIVE_PATTERNS:
            message = pattern.sub(r"\1********", message)
        record.msg = message
        record.args = ()
        return True


def setup_logger(base_dir: Path) -> logging.Logger:
    logs_dir = base_dir / "logs"
    logs_dir.mkdir(parents=True, exist_ok=True)
    log_path = logs_dir / f"onefs-s3-{datetime.now().strftime('%Y%m%d')}.log"

    logger = logging.getLogger("onefs_s3")
    logger.setLevel(logging.INFO)
    logger.handlers.clear()
    logger.propagate = False

    formatter = logging.Formatter("%(asctime)s [%(levelname)s] %(message)s")
    secret_filter = SecretFilter()

    file_handler = logging.FileHandler(log_path, encoding="utf-8")
    file_handler.setFormatter(formatter)
    file_handler.addFilter(secret_filter)
    logger.addHandler(file_handler)

    return logger
