"""Cek heartbeat worker lewat endpoint publik /api/v1/model/info.

Lulus kalau respons 200 dan worker_heartbeat_age_s di bawah ambang
(60 detik). Worker menulis heartbeat ke Redis tiap 30 detik (cron tiap
30 detik di worker), jadi nilai normalnya selalu di bawah ambang ini.
Pemeriksaan ini mendeteksi worker yang macet, antrean Redis tersumbat,
atau image worker yang tidak memuat modul.

Pakai:
    python3 ops/heartbeat_check.py
    python3 ops/heartbeat_check.py --api http://localhost:8000 --max-age 60
    python3 ops/heartbeat_check.py --json      # output JSON untuk monitoring

Kode keluar 0 kalau lulus, 1 kalau worker basi atau endpoint gagal.
"""
import argparse
import json
import sys
import urllib.error
import urllib.request

DEFAULT_API = "http://localhost:8000"
DEFAULT_MAX_AGE = 60


def fetch_model_info(api: str, timeout: int = 10) -> tuple[int, dict | str]:
    """Kembalikan (kode_http, body) dari /api/v1/model/info."""
    url = f"{api.rstrip('/')}/api/v1/model/info"
    try:
        req = urllib.request.Request(url)
        with urllib.request.urlopen(req, timeout=timeout) as resp:
            return resp.status, json.loads(resp.read().decode())
    except urllib.error.HTTPError as exc:
        try:
            body = json.loads(exc.read().decode())
        except json.JSONDecodeError:
            body = exc.read().decode(errors="replace")
        return exc.code, body
    except (urllib.error.URLError, TimeoutError, OSError) as exc:
        return 0, str(exc)


def evaluate(api: str, max_age: int) -> dict:
    """Ambil data model dan nilai heartbeat, kembalikan hasil terstruktur."""
    status, body = fetch_model_info(api)
    if status != 200 or not isinstance(body, dict):
        return {
            "ok": False,
            "http_status": status,
            "error": "endpoint /api/v1/model/info tidak 200",
            "body": body,
        }

    age = body.get("worker_heartbeat_age_s")
    if age is None:
        return {
            "ok": False,
            "http_status": status,
            "error": "kolom worker_heartbeat_age_s tidak ada",
            "body": body,
        }
    try:
        age_value = float(age)
    except (TypeError, ValueError):
        return {
            "ok": False,
            "http_status": status,
            "error": f"worker_heartbeat_age_s bukan angka: {age!r}",
            "body": body,
        }

    return {
        "ok": age_value < max_age,
        "http_status": status,
        "worker_heartbeat_age_s": age_value,
        "threshold_seconds": max_age,
        "engine": body.get("engine"),
        "track_b_loaded": body.get("track_b_loaded"),
        "body": body,
    }


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--api", default=DEFAULT_API)
    parser.add_argument("--max-age", type=int, default=DEFAULT_MAX_AGE)
    parser.add_argument("--json", action="store_true", help="Cetak JSON saja")
    args = parser.parse_args()

    hasil = evaluate(args.api, args.max_age)

    if args.json:
        # Saat --json, jangan bocorkan engine/track_b penuh supaya log tidak
        # penuh derau, hanya field ringkas.
        ringkas = {
            "ok": hasil["ok"],
            "http_status": hasil.get("http_status"),
            "worker_heartbeat_age_s": hasil.get("worker_heartbeat_age_s"),
            "threshold_seconds": hasil.get("threshold_seconds"),
            "error": hasil.get("error"),
        }
        print(json.dumps(ringkas, ensure_ascii=False))
    else:
        if hasil["ok"]:
            print(
                f"[LULUS] heartbeat {hasil['worker_heartbeat_age_s']:.1f}s "
                f"(< {hasil['threshold_seconds']}s) engine={hasil.get('engine')} "
                f"track_b={hasil.get('track_b_loaded')}"
            )
        else:
            print(f"[GAGAL] {hasil.get('error', 'heartbeat basi')}")
            if "worker_heartbeat_age_s" in hasil:
                print(
                    f"  age={hasil['worker_heartbeat_age_s']:.1f}s, "
                    f"ambang={hasil['threshold_seconds']}s"
                )
            if "body" in hasil and hasil["body"]:
                print(f"  body: {json.dumps(hasil['body'], ensure_ascii=False)[:300]}")

    return 0 if hasil["ok"] else 1


if __name__ == "__main__":
    sys.exit(main())