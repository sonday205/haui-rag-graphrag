"""Nhịp gọi chung cho API và CLI trên cùng máy, không thử lại request ngầm."""
from __future__ import annotations

import fcntl
import json
import time
from datetime import datetime, timezone
from pathlib import Path


def reserve_slot(path: Path, interval: float) -> dict:
    if interval < 4.5:
        raise ValueError("Khoảng cách request phải từ 4.5 giây trở lên")
    path.parent.mkdir(parents=True, exist_ok=True)
    started = time.perf_counter()
    with path.open("a+") as file:
        fcntl.flock(file, fcntl.LOCK_EX)
        file.seek(0)
        value = file.read()
        previous = json.loads(value).get("last_start_epoch", 0) if value else 0
        remaining = interval - (time.time() - previous)
        if remaining > 0:
            time.sleep(remaining)
        now = time.time()
        file.seek(0)
        file.truncate()
        json.dump({"last_start_epoch": now, "min_interval_seconds": interval}, file)
        file.flush()
        fcntl.flock(file, fcntl.LOCK_UN)
    return {"request_started_utc": datetime.fromtimestamp(now, timezone.utc).isoformat(),
            "pacing_wait_ms": round((time.perf_counter() - started) * 1000, 2)}
