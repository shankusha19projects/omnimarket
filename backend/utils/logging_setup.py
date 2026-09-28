"""Structured logging to logs/{application,provider,refresh,research,error}.log.

A redaction filter strips anything that looks like an API key or a configured
secret value so credentials never land in log files.
"""
from __future__ import annotations

import json
import logging
import os
import re
from logging.handlers import RotatingFileHandler

from backend.config import LOG_DIR, SECRET_KEYS

_KEY_PATTERNS = [
    re.compile(r"(api[_-]?key|apikey|token|x-api-key|authorization)([\"'=:\s]+)([A-Za-z0-9_\-\.]{8,})", re.I),
    re.compile(r"sk-[A-Za-z0-9_\-]{10,}"),
]


class RedactFilter(logging.Filter):
    def filter(self, record: logging.LogRecord) -> bool:
        msg = record.getMessage()
        for name in SECRET_KEYS:
            val = os.environ.get(name)
            if val and len(val) > 4:
                msg = msg.replace(val, "***")
        msg = _KEY_PATTERNS[0].sub(lambda m: f"{m.group(1)}{m.group(2)}***", msg)
        msg = _KEY_PATTERNS[1].sub("sk-***", msg)
        record.msg, record.args = msg, ()
        return True


class JsonFormatter(logging.Formatter):
    def format(self, record: logging.LogRecord) -> str:
        payload = {
            "ts": self.formatTime(record, "%Y-%m-%dT%H:%M:%S"),
            "level": record.levelname,
            "logger": record.name,
            "msg": record.getMessage(),
        }
        if record.exc_info:
            payload["exc"] = self.formatException(record.exc_info)
        return json.dumps(payload, ensure_ascii=False)


_configured = False


def setup_logging() -> None:
    global _configured
    if _configured:
        return
    _configured = True
    redact = RedactFilter()
    fmt = JsonFormatter()

    def handler(name: str, level: int = logging.INFO) -> RotatingFileHandler:
        h = RotatingFileHandler(LOG_DIR / name, maxBytes=5_000_000, backupCount=3, encoding="utf-8")
        h.setLevel(level)
        h.setFormatter(fmt)
        h.addFilter(redact)
        return h

    root = logging.getLogger("omni")
    root.setLevel(logging.INFO)
    root.addHandler(handler("application.log"))
    root.addHandler(handler("error.log", logging.ERROR))
    console = logging.StreamHandler()
    console.setLevel(logging.WARNING)
    console.addFilter(redact)
    console.setFormatter(logging.Formatter("%(levelname)s %(name)s: %(message)s"))
    root.addHandler(console)

    for sub in ("provider", "refresh", "research"):
        lg = logging.getLogger(f"omni.{sub}")
        lg.addHandler(handler(f"{sub}.log"))


def get_logger(name: str) -> logging.Logger:
    return logging.getLogger(f"omni.{name}")
