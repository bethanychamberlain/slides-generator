"""Usage logger — identity and token counts only, no content."""

import json
import os
from datetime import datetime, timezone
from pathlib import Path

_DATA_DIR = Path(os.environ.get("DATA_DIR", Path(__file__).parent))
LOG_DIR = _DATA_DIR / "usage_logs"


def _log_path():
    """Monthly log file: usage-2026-03.jsonl"""
    LOG_DIR.mkdir(parents=True, exist_ok=True)
    month = datetime.now(timezone.utc).strftime("%Y-%m")
    return LOG_DIR / f"usage-{month}.jsonl"


def log_usage(user_email, action, model, input_tokens=0, output_tokens=0):
    """Append a single usage event. Never logs content, prompts, or filenames."""
    entry = {
        "ts": datetime.now(timezone.utc).isoformat(),
        "user": user_email,
        "action": action,
        "model": model,
        "input_tokens": input_tokens,
        "output_tokens": output_tokens,
    }
    with open(_log_path(), "a") as f:
        f.write(json.dumps(entry) + "\n")
