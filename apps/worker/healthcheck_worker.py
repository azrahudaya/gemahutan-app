"""Healthcheck worker: baca heartbeat dari Redis.

Dipanggil dari Docker HEALTHCHECK. Keluar 0 kalau heartbeat < 90 detik,
1 kalau tidak ada/terlalu tua/Redis tidak bisa dihubungi.
Heartbeat worker adalah JSON: {"engine": "...", "updated_at": "..."}
"""
import json
import os
import sys
import time
from datetime import datetime

import redis

REDIS_URL = os.getenv("REDIS_URL", "redis://redis:6379/0")
HEARTBEAT_KEY = "gemahutan:worker:heartbeat"
MAX_AGE_S = 90


def main():
    if not REDIS_URL:
        print("ERROR: REDIS_URL tidak diisi", file=sys.stderr)
        return 1
    try:
        r = redis.Redis.from_url(REDIS_URL, socket_timeout=5, socket_connect_timeout=5)
        r.ping()
        raw = r.get(HEARTBEAT_KEY)
        if raw is None:
            print(f"KEY_NOT_FOUND: {HEARTBEAT_KEY}", file=sys.stderr)
            return 1
        payload = json.loads(raw)
        updated_at = payload.get("updated_at")
        if not updated_at:
            print("ERROR: heartbeat tidak punya updated_at", file=sys.stderr)
            return 1
        ts = datetime.fromisoformat(updated_at).timestamp()
        age = time.time() - ts
        if age > MAX_AGE_S:
            print(f"STALE: heartbeat age {age:.0f}s > {MAX_AGE_S}s", file=sys.stderr)
            return 1
        print(f"OK: heartbeat age {age:.0f}s")
        return 0
    except Exception as e:
        print(f"ERROR: {e}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    sys.exit(main())