"""Status pipeline inference, dibaca dari sinyal nyata.

Sumber kebenaran:
- Redis key heartbeat yang ditulis worker tiap menit (engine + track yang dimuat).
- Artefak model di image ini, kalau ada (checkpoint Track B dan threshold).

Tidak ada status yang ditulis sebagai konstanta.
"""
import json
import os
from datetime import UTC, datetime
from pathlib import Path

import redis.asyncio as aioredis

from app.config import get_settings

ML_DIR = Path(os.getenv("ML_DIR", "/app/ml"))
HEARTBEAT_KEY = "gemahutan:worker:heartbeat"
HEARTBEAT_STALE_SECONDS = 180

# Batas lokalisasi yang sudah diukur pada rekaman buatan dengan arah dan jarak
# diketahui. Angka dan kalimatnya berasal dari ml/validate_localization.py dan
# catatan sesi di docs/arsip/PROGRESS.md, bukan perkiraan.
BATAS_LOKALISASI = [
    "Satu mikrofon tidak bisa menentukan arah sama sekali; yang bisa ditampilkan hanya lingkaran perkiraan jangkauan deteksi.",
    "Arah butuh minimal dua kanal yang tersinkron, dan pada rekaman buatan galat mediannya 0,0 derajat pada SNR 30 sampai 5 dB.",
    "Jarak dari penyusutan amplitudo sangat sensitif: salah taksir level sumber 6 dB sudah menggeser hasil dua kali lipat (10 m terbaca 20 m).",
    "Triangulasi dua perangkat terpisah 300 m pada galat arah 3 derajat meleset median 14,4 m dan terburuk 56,0 m; dengan tiga perangkat terburuk 27,2 m.",
    "Rekaman buatan belum memuat gema, pantulan, dan kicauan bertumpuk, jadi angka di atas adalah batas atas mutu.",
    "Beberapa perangkat butuh jam yang tersinkron; tanpa itu selisih waktu tiba antar perangkat tidak sah.",
    "Susunan mikrofon segaris tidak bisa memisahkan arah depan dan belakang; sudut cerminnya dilaporkan sebagai arah kembar.",
]


def _nama_track_b() -> str:
    """Nama Track B dibaca dari checkpoint yang benar-benar dipasang.

    Sebelumnya nama ini ditulis tetap sebagai "MLP numpy" padahal model yang
    dipasang bisa model linear. Label yang tidak sesuai modelnya menyesatkan
    siapa pun yang membaca halaman Model.
    """
    ckpt = ML_DIR / "checkpoints" / "best_model.npz"
    if not ckpt.exists():
        return "Classifier embedding BirdNET 1024-dim"
    try:
        import numpy as np

        with np.load(ckpt, allow_pickle=False) as data:
            emb = int(data["W1"].shape[0])
            aktivasi = str(np.asarray(data["activation"]).reshape(-1)[0]) if "activation" in data.files else "relu"
    except Exception:
        return "Classifier embedding BirdNET 1024-dim"
    if aktivasi == "linear":
        return f"Regresi logistik multikelas pada embedding BirdNET {emb}-dim"
    return f"MLP numpy pada embedding BirdNET {emb}-dim"


def _read_json(path: Path):
    try:
        with open(path) as f:
            return json.load(f)
    except Exception:
        return None


async def read_worker_heartbeat() -> dict | None:
    settings = get_settings()
    try:
        client = aioredis.from_url(settings.redis_url)
        raw = await client.get(HEARTBEAT_KEY)
        await client.aclose()
    except Exception:
        return None
    if not raw:
        return None
    try:
        data = json.loads(raw)
    except Exception:
        return None

    ts = data.get("updated_at")
    age = None
    if ts:
        try:
            age = (datetime.now(UTC) - datetime.fromisoformat(ts)).total_seconds()
        except Exception:
            age = None
    data["age_seconds"] = age
    data["fresh"] = age is not None and age <= HEARTBEAT_STALE_SECONDS
    return data


async def get_inference_status() -> dict:
    """Engine apa yang benar-benar dimuat worker, dan artefak apa yang tersedia."""
    engine = os.getenv("INFERENCE_ENGINE", "cascade").strip().lower()
    heartbeat = await read_worker_heartbeat()

    checkpoint_here = (ML_DIR / "checkpoints" / "best_model.npz").exists()
    label_map = _read_json(ML_DIR / "embeddings" / "label_map.json") or {}
    species_local = len([k for k in label_map if k != "_negative"])

    if heartbeat and heartbeat.get("fresh"):
        state = "up"
        detail = f"worker aktif, engine {heartbeat.get('engine', engine)}"
        if heartbeat.get("track_b") is False:
            state = "degraded"
            detail = "worker aktif, tapi Track B tidak dimuat (checkpoint tidak ada di image worker)"
    elif heartbeat:
        state = "degraded"
        detail = (
            "heartbeat worker basi "
            f"({int(heartbeat.get('age_seconds') or 0)}s lalu), pipeline tidak memproses apa pun"
        )
    else:
        state = "unavailable"
        detail = "belum ada heartbeat dari worker, pipeline belum pernah jalan"

    return {
        "state": state,
        "detail": detail,
        "engine": (heartbeat or {}).get("engine", engine),
        "worker_alive": bool(heartbeat and heartbeat.get("fresh")),
        "worker_heartbeat_age_s": heartbeat.get("age_seconds") if heartbeat else None,
        "track_b_checkpoint_in_api_image": checkpoint_here,
        "track_b_species": species_local,
    }


async def get_localization_status() -> dict:
    """Status lokalisasi arah dan jarak, dibaca dari heartbeat worker.

    `terpasang_di_worker` hanya true kalau worker benar-benar melaporkan field
    `localization` di heartbeat. Selama field itu belum ada, jawabannya false apa
    adanya, bukan ditebak dari ketersediaan modul di image API.
    """
    from app.models.tables import Detection

    heartbeat = await read_worker_heartbeat()
    loc = (heartbeat or {}).get("localization")
    if not isinstance(loc, dict):
        loc = {}

    # Sisi API: kolom hasil lokalisasi harus ada dan ikut dikembalikan di respons
    # deteksi, kalau tidak hasil worker akan terbuang di perjalanan.
    kolom = ("azimuth_deg", "azimuth_confidence", "azimuth_kembar_deg", "range_m", "localization_engine")
    disimpan = all(nama in Detection.__table__.columns for nama in kolom)

    catatan = None
    if not loc:
        catatan = (
            "Heartbeat worker belum memuat field localization, "
            "jadi terpasang di worker belum bisa dipastikan."
        )

    return {
        "butuh_kanal_minimal": int(loc.get("kanal_minimal") or 2),
        "butuh_geometri": True,
        "terpasang_di_worker": bool(loc.get("terpasang")),
        "disimpan_ke_deteksi": disimpan,
        "engine": loc.get("engine"),
        "versi": loc.get("versi"),
        "catatan": catatan,
        "batas": BATAS_LOKALISASI,
    }


async def get_model_info() -> dict:
    status = await get_inference_status()
    angka_resmi = _read_json(ML_DIR / "reports" / "angka_resmi.json") or {}
    metrics = _read_json(ML_DIR / "reports" / "metrics.json") or {}
    try:
        from ml.ambang import muat_ambang
        thresholds = muat_ambang(ML_DIR / "reports" / "thresholds.json")
    except Exception:
        thresholds = {}
    meta = _read_json(ML_DIR / "checkpoints" / "meta.json") or {}

    # SHA256 checkpoint dari MANIFEST.json
    checkpoint_sha256 = None
    manifest = _read_json(ML_DIR / "checkpoints" / "MANIFEST.json") or {}
    if "files" in manifest and "best_model.npz" in manifest["files"]:
        checkpoint_sha256 = manifest["files"]["best_model.npz"]["sha256"]

    info = {
        "engine": status["engine"],
        "status": status["state"],
        "status_detail": status["detail"],
        "worker_alive": status["worker_alive"],
        "tracks": [
            {
                "id": "A",
                "name": "BirdNET-Analyzer zero-shot",
                "version": "2.4",
                "species_count": 6522,
                "role": "penjaring awal dengan cakupan global",
                "loaded_by_worker": status["worker_alive"],
            },
            {
                "id": "B",
                "name": _nama_track_b(),
                "species_count": status["track_b_species"],
                "role": "spesialis 25 spesies Indonesia dengan threshold per spesies",
                "checkpoint_in_api_image": status["track_b_checkpoint_in_api_image"],
                "checkpoint_sha256": checkpoint_sha256,
                "epoch": meta.get("epoch"),
                "best_val_acc": meta.get("best_val_acc"),
            },
        ],
        "thresholds_loaded": len(thresholds),
        "thresholds": thresholds,
        "worker_heartbeat_age_s": status.get("worker_heartbeat_age_s"),
    }

    if angka_resmi:
        info["metrics"] = {
            "dataset": "Korpus v3: 8.356 klip (25 spesies target + _negative)",
            "f1_cv": angka_resmi.get("f1_cv"),
            "f1_cv_ci95": angka_resmi.get("f1_cv_ci95"),
            "acc_independen": angka_resmi.get("acc_independen"),
            "f1_independen": angka_resmi.get("f1_independen"),
            "e2e_presisi": angka_resmi.get("e2e_presisi"),
            "e2e_recall": angka_resmi.get("e2e_recall"),
            "sha256_checkpoint": angka_resmi.get("sha256_checkpoint"),
            "sumber": "ml/reports/angka_resmi.json",
        }
    elif metrics:
        info["metrics"] = {
            "test_accuracy": metrics.get("test_acc"),
            "val_accuracy": metrics.get("val_acc"),
            "macro_f1": metrics.get("macro_f1"),
            "sumber": "ml/reports/metrics.json",
        }
    else:
        info["metrics"] = {"note": "Artefak evaluasi tidak ada di image ini, jalankan `make eval`."}

    # Batas yang sudah diukur, dibaca dari laporan evaluasi lapangan di
    # ml/reports/field_metrics.json. Sebelumnya angka di sini ditulis tangan dan
    # menjadi usang tanpa ada yang tahu: nilai lama (xc_noisy 0,6594, inat 0,5082,
    # deteksi palsu 0,6172, bersih 0,7034) berasal dari model sebelum bug dropout
    # diperbaiki, dan angka deteksi palsu yang lama justru lebih rendah dari yang
    # sebenarnya karena dropout acak menekan sebagian deteksi di bawah ambang.
    # Kalau laporan tidak ada, halaman harus mengatakannya, bukan memakai angka lama.
    lapangan_json = _read_json(ML_DIR / "reports" / "field_metrics.json")
    lapangan = None
    if lapangan_json:
        try:
            lapangan = {
                "xc_noisy": lapangan_json["lapangan"]["xc_noisy"]["akurasi_top1"],
                "inat": lapangan_json["lapangan"]["inat"]["akurasi_top1"],
                "deteksi_palsu_pengecoh": lapangan_json["lapangan"]["other"]["deteksi_palsu"],
                "bersih_tanpa_nd": lapangan_json["degradasi"]["bersih_tanpa_nd"]["akurasi_top1"],
            }
        except (KeyError, TypeError):
            lapangan = None

    if lapangan:
        # Desimal ditulis dengan koma supaya konsisten dengan teks Indonesia lain.
        def desimal(nilai: float, digit: int = 4) -> str:
            return f"{nilai:.{digit}f}".replace(".", ",")

        info["limits"] = [
            f"Model lokal mengenal {status['track_b_species']} spesies, kira-kira 1,4 persen dari 1.834 spesies burung Indonesia (Burung Indonesia, 2026).",
            f"Pada rekaman ponsel lapangan (iNaturalist) akurasi top-1 turun ke {desimal(lapangan['inat'])}, dari {desimal(lapangan['bersih_tanpa_nd'])} pada audio bersih.",
            f"Pada kelompok pengecoh di luar daftar model, {desimal(lapangan['deteksi_palsu_pengecoh'] * 100, 1)} persen jendela masih memicu deteksi di atas ambang. Angka ini yang perlu diturunkan dengan verifikasi ahli.",
            "Angka audio bersih berasal dari klip Xeno-canto yang tidak pernah didengar di lapangan, jadi angka itu batas atas, bukan perkiraan lapangan.",
            "Skenario hujan, angin, kota, dan jarak di laporan lapangan adalah simulasi ffmpeg, bukan rekaman lapangan.",
            "Percobaan menambah data simulasi ke latih tidak menaikkan performa lapangan, rincian di ml/reports/field_experiments.md.",
        ]
    else:
        info["limits"] = [
            f"Model lokal mengenal {status['track_b_species']} spesies, kira-kira 1,4 persen dari 1.834 spesies burung Indonesia (Burung Indonesia, 2026).",
            "Angka evaluasi lapangan belum tersedia di image ini. Jalankan evaluasi lapangan lalu rebuild image API, karena halaman ini hanya menampilkan angka yang benar-benar terukur.",
        ]

    if not status["track_b_checkpoint_in_api_image"]:
        info["warning"] = (
            "Checkpoint Track B tidak ada di image API, jadi klasifikasi spesies lokal "
            "hanya jalan di worker. Latih ulang dengan `make train` kalau artefak ini hilang."
        )

    info["localization"] = await get_localization_status()
    return info
