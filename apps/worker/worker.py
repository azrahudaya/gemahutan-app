"""ARQ worker: proses rekaman (inference + indeks soundscape) dengan heartbeat.

Alur satu rekaman:
1. ambil baris recording + job, tandai processing, tulis tahap dan progres
2. unduh audio dari MinIO
3. siapkan audio: mono untuk model, salinan tanpa downmix untuk lokalisasi
4. inference (CascadeEngine kalau artefak Track B ada, kalau tidak BirdNET Analyzer)
5. simpan deteksi, lalu hitung arah dan jangkauan per deteksi
6. hitung indeks soundscape (ACI, NDSI, ADI, BI) dengan scikit-maad
7. render spektrogram ke cache MinIO supaya permintaan pertama dari UI cepat
8. tandai done

Setiap tahap menulis jobs.stage dan jobs.progress, bukan hanya di akhir, supaya
UI dan laporan batch menampilkan proses yang sedang berjalan. Kalau satu tahap
gagal, stage jadi gagal dan progres berhenti di angka terakhir.

Worker juga menulis heartbeat ke Redis dan menyapu job yang nyangkut, supaya
rekaman tidak tersangkut pending tanpa ada yang memproses.
"""
import json
import logging
import math
import os
import smtplib
import subprocess
import tempfile
import threading
from dataclasses import dataclass, field
from datetime import UTC, datetime, timedelta
from email.message import EmailMessage
from pathlib import Path

import boto3
import numpy as np
from arq import cron
from arq.connections import RedisSettings
from sqlalchemy import create_engine, text
from sqlalchemy.orm import Session

# Modul lokalisasi ada di image worker (PYTHONPATH=/app). Importnya di dalam try
# supaya worker tetap hidup kalau ml/ tidak ikut, dan heartbeat melaporkan
# dengan jujur bahwa lokalisasi tidak terpasang.
try:
    import ml.localization as modul_lokalisasi

    LOKALISASI_TERSEDIA = True
except Exception as _exc:  # pragma: no cover - hanya kalau ml/ tidak ada
    modul_lokalisasi = None
    LOKALISASI_TERSEDIA = False
    print(f"[worker] modul lokalisasi tidak bisa dimuat: {_exc}")

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("worker")

S3_ENDPOINT = os.getenv("S3_ENDPOINT", "http://minio:9000")
S3_ACCESS_KEY = os.getenv("S3_ACCESS_KEY", "minioadmin")
S3_SECRET_KEY = os.getenv("S3_SECRET_KEY", "minioadmin")
S3_BUCKET = os.getenv("S3_BUCKET", "gemahutan-audio")
REDIS_URL = os.getenv("REDIS_URL", "redis://redis:6379/0")
DATABASE_URL = os.getenv("DATABASE_URL_SYNC", "postgresql://gemahutan:gemahutan@db:5432/gemahutan")

# Email aplikasi (peringatan spesies prioritas). Kredensial dibaca dari
# /etc/gemahutan/notif.env lewat env_file, sama seperti notifikasi server.
SMTP_HOST = os.getenv("SMTP_HOST", "smtp.gmail.com")
SMTP_PORT = int(os.getenv("SMTP_PORT", "587"))
SMTP_USER = os.getenv("SMTP_USER", "")
SMTP_APP_PASSWORD = os.getenv("SMTP_APP_PASSWORD", "")
SMTP_FROM = os.getenv("SMTP_FROM", SMTP_USER)
# Jeda minimal antar email untuk satu spesies di satu lokasi.
JEDA_PERINGATAN_JAM = int(os.getenv("JEDA_PERINGATAN_JAM", "6"))


def _dsn_dengan_driver_tegas(dsn: str) -> str:
    """Pastikan DSN menyebut driver psycopg2 secara eksplisit.

    SQLAlchemy 2.1 mengubah driver bawaan untuk URL `postgresql://` dari
    psycopg2 menjadi psycopg (v3). Image worker memasang psycopg2-binary, dan
    requirements-nya tidak dipin (`sqlalchemy>=2.0,<3`), jadi begitu image
    dibangun ulang dan menarik SQLAlchemy 2.1 seluruh job langsung mati dengan
    ModuleNotFoundError: No module named 'psycopg'. Gejalanya menyesatkan:
    job menumpuk di status pending tanpa pesan galat di tabel jobs, karena
    worker gagal justru saat membuka koneksi untuk menulis status.

    Menyebut driver secara eksplisit membuat pilihan dialek tidak lagi
    bergantung pada versi SQLAlchemy. `.env` tetap boleh memakai
    `postgresql://` karena berkas itu dipakai bersama dengan API yang memasang
    psycopg v3.
    """
    if dsn.startswith("postgresql://"):
        return dsn.replace("postgresql://", "postgresql+psycopg2://", 1)
    return dsn


DATABASE_URL = _dsn_dengan_driver_tegas(DATABASE_URL)
ML_DIR = Path(os.getenv("ML_DIR", "/app/ml"))
HEARTBEAT_KEY = "gemahutan:worker:heartbeat"

s3 = boto3.client(
    "s3",
    endpoint_url=S3_ENDPOINT,
    aws_access_key_id=S3_ACCESS_KEY,
    aws_secret_access_key=S3_SECRET_KEY,
    region_name="us-east-1",
)

_engine = None
_engine_name = None
_track_b = False

# TFLite interpreter TIDAK aman dipakai dua thread sekaligus. Worker memproses
# sampai max_jobs rekaman serentak dan tiap job menjalankan inferensi lewat
# asyncio.to_thread, jadi dua thread bisa memegang interpreter yang sama.
# birdnetlib memanggil resize_tensor_input + allocate_tensors per jendela, dan
# realokasi di satu thread sementara thread lain sedang membaca tensor memberi
# galat "There is at least 1 reference to internal data in the interpreter".
#
# Terukur pada `make demo` 1 Okt: 4 dari 10 job gagal, semuanya di jendela saat
# job pertama masih memuat engine; job sesudah pemuatan selesai semuanya lulus.
#
# _kunci_muat  : supaya engine dibangun SEKALI walau beberapa thread memintanya
#                berbarengan (tanpa ini dua thread sama-sama lolos cek `is None`).
# _kunci_inferensi: membuat pemakaian interpreter berurutan. Ini mengurangi
#                paralelisme, tapi inferensi memang terikat CPU dan sudah
#                multi-thread di dalam TFLite, jadi yang hilang kecil
#                dibandingkan job yang gagal.
_kunci_muat = threading.Lock()
_kunci_inferensi = threading.Lock()
# Format yang bisa didekode librosa langsung. Selain ini dikonversi dulu ke wav.
DECODE_LANGSUNG = {".wav", ".mp3", ".flac", ".ogg", ".opus", ".aiff", ".aif"}
# Batas percobaan satu rekaman. Tanpa batas, rekaman yang berkasnya rusak bisa
# dicoba ulang tanpa henti dan menutupi antrean.
MAX_ATTEMPTS = int(os.getenv("MAX_JOB_ATTEMPTS", "3"))
# Di bawah ini, deteksi dianggap belum cukup kuat untuk ditampilkan sendiri.
MIN_DURASI_DETEKSI_S = 1.0
MIN_KEMUNCULAN_ULANG = 2
AMBANG_KUAT = 0.5

# Tahap dan progres job, dipatok kontrak Fase 2. Angkanya tetap supaya UI,
# laporan batch, dan log memakai skala yang sama.
PROGRES = {
    "antre": 0,
    "unduh": 10,
    "dekode": 20,
    "birdnet": 30,
    "birdnet_selesai": 60,
    "klasifikasi": 60,
    "klasifikasi_selesai": 75,
    "lokalisasi": 80,
    "indeks": 88,
    "spektrogram": 96,
    "selesai": 100,
}
TAHAP = (
    "antre", "unduh", "dekode", "birdnet", "klasifikasi",
    "lokalisasi", "indeks", "spektrogram", "selesai", "gagal",
)

# Lokalisasi butuh minimal dua kanal yang tersinkron. Satu kanal tidak punya
# selisih waktu tiba yang bisa diukur.
KANAL_MINIMAL_LOKALISASI = 2
# Jendela yang dipakai mengukur arah dipotong supaya biaya FFT tidak ikut
# panjang rekaman. Deteksi kicauan jarang lebih panjang dari ini.
MAX_JENDELA_LOKALISASI_S = 4.0
# Kunci cache spektrogram di MinIO. Bentuknya harus sama dengan
# apps/api/app/services/spectrogram_cache.py, kalau tidak API tidak menemukan
# hasil render worker dan merender ulang.
CACHE_SPEKTROGRAM_PREFIX = "cache/spectrogram"

_KOLOM: dict[str, set[str]] = {}
_PERINGATAN_SEKALI: set[str] = set()


def _load_thresholds() -> dict:
    try:
        from ml.ambang import muat_ambang
        return muat_ambang(ML_DIR / "reports" / "thresholds.json")
    except Exception:
        return {}


def _peringatan_sekali(kunci: str, pesan: str) -> None:
    """Catat peringatan yang sama sekali saja, jangan banjiri log tiap rekaman."""
    if kunci not in _PERINGATAN_SEKALI:
        _PERINGATAN_SEKALI.add(kunci)
        logger.warning(pesan)


def kolom_tabel(session: Session, tabel: str, segarkan: bool = False) -> set[str]:
    """Nama kolom satu tabel, di-cache selama worker hidup.

    Dipakai supaya worker tetap memproses rekaman walau migrasi kolom baru
    belum jalan. Tanpa ini, satu kolom yang belum ada membuat seluruh rekaman
    gagal.

    Args:
        segarkan: paksa baca ulang skema dari database.
    """
    if segarkan or tabel not in _KOLOM:
        baris = session.execute(
            text("SELECT column_name FROM information_schema.columns WHERE table_name = :tabel"),
            {"tabel": tabel},
        ).all()
        _KOLOM[tabel] = {r[0] for r in baris}
    return _KOLOM[tabel]


def tulis_progres(session: Session, recording_id: int, tahap: str, progress: int) -> None:
    """Tulis jobs.stage dan jobs.progress satu rekaman, lalu commit.

    Dipanggil setelah setiap tahap. Kalau kolomnya belum ada, worker mencatat
    peringatan sekali lalu jalan terus.
    """
    if tahap not in TAHAP:
        raise ValueError(f"tahap tidak dikenal: {tahap}")

    kolom = kolom_tabel(session, "jobs")
    if not {"stage", "progress"} <= kolom:
        kolom = kolom_tabel(session, "jobs", segarkan=True)

    setel = []
    nilai: dict = {"rid": recording_id}
    if "stage" in kolom:
        setel.append("stage = :tahap")
        nilai["tahap"] = tahap
    if "progress" in kolom:
        setel.append("progress = :progress")
        nilai["progress"] = int(progress)

    if not setel:
        _peringatan_sekali(
            "jobs_tanpa_progres",
            "Kolom jobs.stage dan jobs.progress belum ada, tahap dan progres tidak dicatat",
        )
        return

    session.execute(
        text(f"UPDATE jobs SET {', '.join(setel)} WHERE recording_id = :rid"),
        nilai,
    )
    session.commit()
    logger.info("Rekaman %s tahap %s, progres %d", recording_id, tahap, progress)


def get_engine():
    """Pilih engine sekali saja, laporkan apa yang benar-benar dimuat.

    Pemuatan dikunci: tanpa itu dua thread job bisa sama-sama lolos cek
    `is None` lalu membangun dua interpreter TFLite, dan yang satu merealokasi
    tensor saat yang lain sedang memakainya.
    """
    global _engine, _engine_name, _track_b
    if _engine is not None or _engine_name is not None:
        return _engine

    with _kunci_muat:
        # Dicek ulang DI DALAM kunci: thread lain mungkin sudah selesai memuat
        # selama thread ini menunggu.
        if _engine is not None or _engine_name is not None:
            return _engine
        return _muat_engine()


def _muat_engine():
    """Isi _engine/_engine_name/_track_b. Hanya dipanggil dari get_engine()."""
    global _engine, _engine_name, _track_b

    engine_type = os.getenv("INFERENCE_ENGINE", "cascade").strip().lower()
    checkpoint = ML_DIR / "checkpoints" / "best_model.npz"

    if engine_type == "cascade" and checkpoint.exists():
        try:
            import sys
            if str(ML_DIR.parent) not in sys.path:
                sys.path.insert(0, str(ML_DIR.parent))
            from ml.engines.cascade import CascadeEngine
            _engine = CascadeEngine()
            _engine._ensure_loaded()
            _engine_name = "cascade"
            _track_b = True
            logger.info(
                "CascadeEngine aktif: BirdNET + MLP %d spesies Indonesia",
                _engine._embed_clf.species_count(),
            )
            return _engine
        except Exception as exc:
            logger.warning("CascadeEngine gagal dimuat (%s), jatuh ke BirdNET saja", exc)

    if engine_type in ("cascade", "birdnet"):
        try:
            from birdnetlib.analyzer import Analyzer
            _engine = Analyzer()
            _engine_name = "birdnet"
            logger.info("BirdNET Analyzer aktif (zero-shot). Track B tidak dimuat.")
            return _engine
        except Exception as exc:
            logger.warning("BirdNET gagal dimuat (%s), pakai stub", exc)

    _engine = None
    _engine_name = "stub"
    logger.info("Engine stub: pipeline jalan tanpa inference")
    return _engine


def run_inference(audio_path, lat=None, lon=None, min_conf=0.1, lapor_tahap=None):
    """Kembalikan list dict deteksi, seragam untuk kedua engine.

    Args:
        lapor_tahap: callback (tahap, progress) yang dipanggil engine di tengah
            proses, dipakai menulis progres BirdNET sebelum klasifikasi mulai.
    """
    engine = get_engine()

    if _engine_name == "cascade":
        # Satu interpreter TFLite, satu pemakai pada satu waktu. Lihat catatan
        # di _kunci_inferensi.
        with _kunci_inferensi:
            if lapor_tahap is None:
                results = engine.predict(audio_path, lat=lat, lon=lon, min_conf=min_conf)
            else:
                results = engine.predict(
                    audio_path, lat=lat, lon=lon, min_conf=min_conf,
                    progress_cb=lapor_tahap,
                )
        return [
            {
                "scientific_name": r.species_scientific,
                "common_name": r.species_common,
                "confidence": float(r.confidence),
                "start_s": float(r.start_s),
                "end_s": float(r.end_s),
                "engine": r.engine,
                "engine_version": r.engine_version,
            }
            for r in results
        ]

    if _engine_name == "birdnet":
        from birdnetlib import Recording
        kwargs = {"min_conf": min_conf}
        if lat is not None and lon is not None:
            kwargs["lat"] = lat
            kwargs["lon"] = lon
        rec = Recording(engine, audio_path, date=datetime.now(), **kwargs)
        # Jalur cadangan ini memakai Analyzer yang sama, jadi interpreternya
        # juga harus dipakai berurutan.
        with _kunci_inferensi:
            rec.analyze()
        return [
            {
                "scientific_name": d["scientific_name"],
                "common_name": d["common_name"],
                "confidence": float(d["confidence"]),
                "start_s": float(d["start_time"]),
                "end_s": float(d["end_time"]),
                "engine": "BirdNET-Analyzer",
                "engine_version": "2.4",
            }
            for d in rec.detections
        ]

    return []


@dataclass
class AudioJalur:
    """Hasil penyiapan audio satu rekaman.

    mono adalah jalur untuk model, multikanal adalah salinan tanpa downmix untuk
    lokalisasi. multikanal None kalau berkas sumber hanya punya satu kanal.
    """

    mono: Path
    multikanal: Path | None
    kanal: int
    dibuat: list[Path] = field(default_factory=list)

    def bersihkan(self) -> None:
        for berkas in self.dibuat:
            try:
                if berkas.exists():
                    berkas.unlink()
            except OSError as exc:
                logger.warning("Gagal hapus berkas sementara %s: %s", berkas, exc)


def hitung_kanal(jalur: Path) -> int:
    """Jumlah kanal berkas audio, 1 kalau tidak bisa dibaca.

    Salah menghitung di sini berbahaya: kanal yang dikira mono akan dipaksa
    downmix dan arah suara hilang tanpa jejak.
    """
    try:
        import soundfile as sf
        return int(sf.info(str(jalur)).channels)
    except Exception:
        pass
    try:
        proses = subprocess.run(
            ["ffprobe", "-v", "error", "-select_streams", "a:0", "-show_entries",
             "stream=channels", "-of", "default=nw=1:nk=1", str(jalur)],
            capture_output=True,
            text=True,
        )
        keluaran = proses.stdout.strip()
        if proses.returncode == 0 and keluaran.isdigit():
            return int(keluaran)
    except Exception as exc:
        logger.warning("Jumlah kanal %s tidak terbaca (%s), dianggap mono", jalur, exc)
    return 1


def _konversi(masuk: Path, keluar: Path, kanal: int) -> None:
    """Jalankan ffmpeg untuk menyiapkan satu versi audio."""
    proses = subprocess.run(
        ["ffmpeg", "-y", "-hide_banner", "-loglevel", "error", "-i", str(masuk),
         "-ar", "48000", "-ac", str(kanal), str(keluar)],
        capture_output=True,
        text=True,
    )
    if proses.returncode != 0 or not keluar.exists():
        raise RuntimeError(f"konversi audio {masuk.suffix} gagal: {proses.stderr.strip()[:150]}")


def siapkan_audio(tmp_path: Path) -> Path:
    """Kembalikan jalur audio mono yang bisa didekode librosa.

    API menerima unggahan m4a dan aac karena rekaman ponsel biasanya begitu,
    sedangkan librosa hanya membaca wav, mp3, flac, dan ogg. Tanpa langkah ini,
    unggahan m4a lolos validasi API lalu gagal di worker. Mono dipaksa karena
    model dilatih pada audio satu kanal.
    """
    if tmp_path.suffix.lower() in DECODE_LANGSUNG and hitung_kanal(tmp_path) <= 1:
        return tmp_path
    tujuan = tmp_path.with_suffix(".mono.wav")
    _konversi(tmp_path, tujuan, 1)
    logger.info("Audio %s dikonversi ke wav mono sebelum inference", tmp_path.suffix)
    return tujuan


def siapkan_audio_jalur(tmp_path: Path) -> AudioJalur:
    """Siapkan dua jalur audio: mono untuk model, multikanal untuk lokalisasi.

    Downmix hanya untuk model. Arah suara diukur dari selisih waktu tiba antar
    mikrofon, jadi kanal aslinya harus utuh dan tidak boleh diratakan.
    """
    kanal = hitung_kanal(tmp_path)
    langsung = tmp_path.suffix.lower() in DECODE_LANGSUNG
    dibuat: list[Path] = []

    mono = siapkan_audio(tmp_path)
    if mono != tmp_path:
        dibuat.append(mono)

    if kanal < KANAL_MINIMAL_LOKALISASI:
        return AudioJalur(mono=mono, multikanal=None, kanal=kanal, dibuat=dibuat)

    if langsung:
        # Berkas sumber sudah wav atau flac, jadi salinannya adalah berkas itu.
        multikanal = tmp_path
    else:
        multikanal = tmp_path.with_suffix(".multikanal.wav")
        _konversi(tmp_path, multikanal, kanal)
        dibuat.append(multikanal)
        logger.info("Audio %s disimpan ulang sebagai %d kanal untuk lokalisasi", tmp_path.suffix, kanal)

    return AudioJalur(mono=mono, multikanal=multikanal, kanal=kanal, dibuat=dibuat)


def muat_multikanal(jalur: Path) -> tuple[np.ndarray, int]:
    """Baca audio multikanal tanpa downmix: data (kanal, sampel) dan sample rate."""
    import soundfile as sf

    data, sr = sf.read(str(jalur), always_2d=True, dtype="float32")
    return np.ascontiguousarray(data.T), int(sr)


def compute_acoustic_indices(audio_path):
    """ACI, NDSI, ADI, BI dari scikit-maad.

    Audio didekode dengan librosa (wav, mp3, flac, ogg). maad.sound.load hanya
    menerima wav, itu sebabnya versi lama selalu menghasilkan null untuk mp3.

    Audio sunyi menghasilkan NaN, bukan galat: ACI membagi dengan jumlah per
    baris dan NDSI/BI membagi dengan total energi, jadi penyebut nol
    menghasilkan NaN tanpa exception. Nilai NaN tidak boleh masuk database
    karena json.dumps menolaknya dan endpoint /indices menjawab 500 (gejalanya
    di browser tampak seperti galat CORS, bukan galat server). Karena itu setiap
    hasil diperiksa isfinite dan audio yang benar-benar sunyi ditolak lebih dulu.
    """
    import librosa
    from maad import features, sound

    try:
        s, fs = librosa.load(audio_path, sr=None, mono=True)
    except Exception as exc:
        logger.warning("Gagal dekode audio untuk indeks: %s", exc)
        return {"aci": None, "ndsi": None, "adi": None, "bi": None}, f"decode gagal: {exc}"

    if s.size == 0:
        return {"aci": None, "ndsi": None, "adi": None, "bi": None}, "audio kosong"

    if not np.any(s):
        return {"aci": None, "ndsi": None, "adi": None, "bi": None}, "audio sunyi, indeks tidak bermakna"

    Sxx, tn, fn, ext = sound.spectrogram(s, fs)
    out: dict[str, float | None] = {"aci": None, "ndsi": None, "adi": None, "bi": None}
    failed = []

    def simpan(kunci, nilai):
        """Simpan hanya nilai berhingga. NaN dan inf dicatat sebagai kegagalan."""
        nilai = float(nilai)
        if not np.isfinite(nilai):
            failed.append(f"{kunci}: hasil tidak berhingga")
            return
        out[kunci] = nilai

    try:
        # maad 1.5 mengembalikan (aci_per_bin, aci_per_frame, aci_sum)
        aci_result = features.acoustic_complexity_index(Sxx)
        simpan("aci", np.asarray(aci_result[2]).ravel()[0])
    except Exception as exc:
        failed.append(f"aci: {exc}")

    try:
        # maad 1.5 mengembalikan (NDSI, ratio bio/antro, energi antro, energi bio).
        ndsi_result = features.soundscape_index(
            Sxx ** 2, fn, flim_bioPh=(1000, 10000), flim_antroPh=(0, 1000)
        )
        simpan("ndsi", ndsi_result[0])
    except Exception as exc:
        failed.append(f"ndsi: {exc}")

    try:
        simpan("adi", features.acoustic_diversity_index(
            Sxx, fn, fmin=0, fmax=min(10000, int(fs / 2)), bin_step=1000, index="shannon"
        ))
    except Exception as exc:
        failed.append(f"adi: {exc}")

    try:
        simpan("bi", features.bioacoustics_index(Sxx, fn))
    except Exception as exc:
        failed.append(f"bi: {exc}")

    note = None if not failed else "sebagian indeks gagal: " + "; ".join(failed)[:400]
    return out, note


def geometri_linier(jumlah_kanal: int, spacing_m: float) -> list[tuple[float, float]]:
    """Mikrofon berbaris di sumbu x, kanal i di x = i kali jarak antar mikrofon."""
    return [(i * spacing_m, 0.0) for i in range(jumlah_kanal)]


def level_rms_db(potongan: list[np.ndarray]) -> float:
    """Level RMS jendela deteksi dalam dBFS, dirata-rata antar kanal.

    Satuannya harus sama dengan level referensi di kolom devices, karena
    selisihnya yang dipakai menghitung jarak.
    """
    daya = [float(np.mean(np.square(np.asarray(k, dtype=np.float64)))) for k in potongan]
    rerata = float(np.mean(daya)) if daya else 0.0
    return 20.0 * math.log10(math.sqrt(rerata) + 1e-12)


def lokalisasi_jendela(data_kanal: np.ndarray | None, sr: int, geometri: list[tuple[float, float]] | None,
                       mulai_s: float, akhir_s: float,
                       acuan_jarak: tuple[float, float] | None = None) -> dict:
    """Arah datang dan jangkauan satu jendela deteksi.

    Nilai yang tidak bisa dihitung dikembalikan None, bukan nol. Arah 0 derajat
    adalah arah yang sah, jadi nol palsu akan terbaca sebagai hasil pengukuran.
    """
    kosong: dict[str, float | str | None] = {
        "azimuth_deg": None,
        "azimuth_confidence": None,
        "azimuth_kembar_deg": None,
        "range_m": None,
        "localization_engine": None,
    }
    if not LOKALISASI_TERSEDIA or modul_lokalisasi is None or data_kanal is None or geometri is None:
        return kosong

    jumlah_kanal = min(int(data_kanal.shape[0]), len(geometri))
    if jumlah_kanal < KANAL_MINIMAL_LOKALISASI or sr <= 0:
        return kosong

    mulai = max(0, int(round(mulai_s * sr)))
    akhir = min(int(data_kanal.shape[1]), int(round(akhir_s * sr)))
    akhir = min(akhir, mulai + int(MAX_JENDELA_LOKALISASI_S * sr))
    if akhir - mulai < 2:
        return kosong

    potongan = [
        np.asarray(data_kanal[i, mulai:akhir], dtype=np.float64) for i in range(jumlah_kanal)
    ]
    hasil_arah = modul_lokalisasi.estimasi_arah(potongan, sr, geometri[:jumlah_kanal])
    if hasil_arah is None:
        return kosong

    kosong["azimuth_deg"] = float(hasil_arah.azimuth_deg)
    kosong["azimuth_confidence"] = float(hasil_arah.keyakinan)
    kosong["localization_engine"] = modul_lokalisasi.ENGINE_NAME
    if hasil_arah.arah_kembar:
        # Susunan mikrofon segaris tidak memisahkan depan dan belakang, jadi
        # sudut cerminnya disimpan supaya satu arah tidak dilaporkan sebagai
        # satu-satunya kemungkinan.
        kosong["azimuth_kembar_deg"] = float(hasil_arah.arah_kembar[0])

    if acuan_jarak is not None:
        # Acuan jarak hanya sah kalau perangkat pernah dikalibrasi. Level diukur
        # pada jendela deteksi yang sama dengan pengukuran arah.
        jarak_ref, level_ref = acuan_jarak
        kosong["range_m"] = modul_lokalisasi.jarak_dari_selisih_level(
            level_rms_db(potongan), level_ref, jarak_ref
        )
    return kosong


def baca_acuan_perangkat(session: Session, recording_id: int) -> tuple[float | None, tuple[float, float] | None]:
    """Geometri dan acuan jarak perangkat yang dipakai satu rekaman.

    Kembalikan (mic_spacing_m, (reference_distance_m, reference_level_db)).
    Semuanya None kalau rekaman tidak punya perangkat atau kolomnya belum ada,
    dan itu berarti lokalisasi dilewati, bukan ditebak.
    """
    kolom = kolom_tabel(session, "devices")
    if "mic_spacing_m" not in kolom:
        _peringatan_sekali(
            "devices_tanpa_geometri",
            "Kolom devices.mic_spacing_m belum ada, arah tidak dihitung",
        )
        return None, None

    pilih = ["d.mic_spacing_m"]
    for nama in ("reference_distance_m", "reference_level_db"):
        pilih.append(f"d.{nama}" if nama in kolom else f"NULL AS {nama}")

    baris = session.execute(
        text(
            f"SELECT {', '.join(pilih)} FROM recordings r "
            "LEFT JOIN devices d ON d.id = r.device_id WHERE r.id = :rid"
        ),
        {"rid": recording_id},
    ).fetchone()
    if not baris:
        return None, None

    spacing = float(baris[0]) if baris[0] else None
    if baris[1] is None or baris[2] is None:
        acuan = None
    else:
        acuan = (float(baris[1]), float(baris[2]))
    return spacing, acuan


def simpan_spektrogram(audio: Path, storage_key: str) -> bool:
    """Render spektrogram ke cache MinIO dengan kunci yang dipakai API.

    API merender spektrogram saat diminta lalu menyimpannya di cache. Pekerjaan
    itu dikerjakan lebih dulu di worker supaya permintaan pertama dari UI tidak
    menunggu render. Gagal di sini tidak membatalkan rekaman, API masih bisa
    merender sendiri.
    """
    try:
        import io

        import librosa
        import librosa.display
        import matplotlib
        matplotlib.use("Agg")
        import matplotlib.pyplot as plt

        y, sr = librosa.load(str(audio), sr=None, mono=True)
        if y.size == 0:
            logger.warning("Spektrogram dilewati: audio kosong")
            return False

        spek = librosa.feature.melspectrogram(y=y, sr=sr, n_mels=128, fmax=sr // 2)
        spek_db = librosa.power_to_db(spek, ref=np.max)

        fig, ax = plt.subplots(1, 1, figsize=(12, 4), dpi=100)
        fig.patch.set_facecolor("#101010")
        ax.set_facecolor("#101010")
        gambar = librosa.display.specshow(spek_db, sr=sr, x_axis="time", y_axis="mel",
                                          ax=ax, cmap="magma")
        bilah = fig.colorbar(gambar, ax=ax, format="%+2.0f dB")
        ax.set_title("")
        for teks in (ax.xaxis.label, ax.yaxis.label, *ax.get_xticklabels(), *ax.get_yticklabels()):
            teks.set_color("#D4D4D8")
        for tulang in ax.spines.values():
            tulang.set_color("#27272A")
        bilah.ax.tick_params(colors="#D4D4D8")
        bilah.outline.set_edgecolor("#27272A")
        fig.tight_layout()

        penyangga = io.BytesIO()
        fig.savefig(penyangga, format="png", bbox_inches="tight", pad_inches=0.1)
        plt.close(fig)
        isi = penyangga.getvalue()

        s3.put_object(
            Bucket=S3_BUCKET,
            Key=f"{CACHE_SPEKTROGRAM_PREFIX}/{storage_key}.png",
            Body=isi,
            ContentType="image/png",
        )
        logger.info("Spektrogram %s disimpan ke cache (%d byte)", storage_key, len(isi))
        return True
    except Exception as exc:
        logger.warning("Spektrogram %s gagal dibuat: %s", storage_key, exc)
        return False


def info_lokalisasi() -> dict:
    """Blok lokalisasi untuk heartbeat worker. Bentuknya dikunci kontrak."""
    return {
        "terpasang": LOKALISASI_TERSEDIA,
        "kanal_minimal": KANAL_MINIMAL_LOKALISASI,
        "engine": getattr(modul_lokalisasi, "ENGINE_NAME", "tidak terpasang"),
        "versi": getattr(modul_lokalisasi, "ENGINE_VERSION", "0"),
    }


async def write_heartbeat(ctx=None):
    """Tanda hidup worker + engine yang benar-benar dimuat + status lokalisasi."""
    import redis.asyncio as aioredis

    payload = {
        "engine": _engine_name or os.getenv("INFERENCE_ENGINE", "cascade"),
        "track_b": _track_b,
        "localization": info_lokalisasi(),
        "updated_at": datetime.now(UTC).isoformat(),
    }
    try:
        client = aioredis.from_url(REDIS_URL)
        await client.set(HEARTBEAT_KEY, json.dumps(payload), ex=900)
        await client.aclose()
    except Exception as exc:
        logger.warning("Gagal menulis heartbeat: %s", exc)


async def sweep_stuck_jobs(ctx):
    """Bersihkan job yang tidak pernah diproses atau mati di tengah jalan."""
    redis = ctx["redis"]
    engine = create_engine(DATABASE_URL)

    with Session(engine) as session:
        # Job running yang ditinggal worker (restart) > 20 menit: tandai failed.
        stale = session.execute(
            text(
                """
                UPDATE jobs SET status = 'failed',
                                last_error = 'worker berhenti saat job berjalan, silakan retry',
                                finished_at = NOW()
                WHERE status = 'running' AND started_at < NOW() - INTERVAL '20 minutes'
                RETURNING recording_id
                """
            )
        ).all()
        if stale:
            for (rid,) in stale:
                session.execute(
                    text(
                        "UPDATE recordings SET status = 'failed', "
                        "error_message = 'job terputus, silakan retry' WHERE id = :id"
                    ),
                    {"id": rid},
                )
            logger.warning("%d job running basi ditandai failed", len(stale))

        # Job pending yang belum pernah masuk antrean: masukkan ulang.
        # Tabel jobs tidak menyimpan created_at, jadi umur job dibaca dari
        # kapan rekamannya dibuat.
        pending = session.execute(
            text(
                """
                SELECT j.recording_id FROM jobs j
                JOIN recordings r ON r.id = j.recording_id
                WHERE j.status = 'pending'
                  AND j.attempts = 0
                  AND r.created_at < NOW() - INTERVAL '2 minutes'
                ORDER BY j.id
                LIMIT 20
                """
            )
        ).all()
        session.commit()

    for (recording_id,) in pending:
        try:
            await redis.enqueue_job("process_recording", recording_id)
            logger.info("Sweep: rekaman %s dimasukkan ulang ke antrean", recording_id)
        except Exception as exc:
            logger.warning("Sweep gagal enqueue rekaman %s: %s", recording_id, exc)


def terapkan_lokalisasi(session: Session, id_deteksi: list[tuple[int, dict]], jalur_multikanal: Path | None,
                        kanal: int, spacing_m: float | None, acuan_jarak: tuple[float, float] | None) -> int:
    """Isi arah dan jangkauan tiap baris deteksi dari audio multikanal.

    Kembalikan jumlah deteksi yang dapat arahnya. Nol berarti syaratnya tidak
    terpenuhi: kanal kurang dari dua, perangkat belum punya mic_spacing_m, kolom
    lokalisasi belum ada, atau seluruh jendela gagal diukur. Kolomnya dibiarkan
    kosong, bukan diisi nol.
    """
    if not id_deteksi or jalur_multikanal is None or not spacing_m or kanal < KANAL_MINIMAL_LOKALISASI:
        return 0
    if not {
        "azimuth_deg", "azimuth_confidence", "azimuth_kembar_deg", "range_m",
        "localization_engine",
    } <= kolom_tabel(session, "detections", segarkan=True):
        _peringatan_sekali(
            "detections_tanpa_lokalisasi",
            "Kolom lokalisasi di detections belum ada, arah tidak disimpan",
        )
        return 0

    geometri = geometri_linier(kanal, float(spacing_m))
    data_kanal, sr_kanal = muat_multikanal(jalur_multikanal)

    jumlah_arah = 0
    for deteksi_id, d in id_deteksi:
        hasil = lokalisasi_jendela(
            data_kanal, sr_kanal, geometri,
            float(d["start_s"]), float(d["end_s"]), acuan_jarak,
        )
        if hasil["azimuth_deg"] is None:
            continue
        session.execute(
            text(
                """
                UPDATE detections
                   SET azimuth_deg = :az, azimuth_confidence = :conf,
                       azimuth_kembar_deg = :kembar,
                       range_m = :jarak, localization_engine = :eng
                 WHERE id = :id
                """
            ),
            {
                "az": hasil["azimuth_deg"],
                "conf": hasil["azimuth_confidence"],
                "kembar": hasil["azimuth_kembar_deg"],
                "jarak": hasil["range_m"],
                "eng": hasil["localization_engine"],
                "id": deteksi_id,
            },
        )
        jumlah_arah += 1
    session.commit()
    return jumlah_arah


async def process_recording(ctx, recording_id: int):
    """Unduh audio, jalankan inference, simpan deteksi, arah, indeks, spektrogram.

    Seluruh isi dijalankan di thread executor supaya tidak memblokir event loop
    (heartbeat, sweep, dan job lain tetap berjalan)."""
    import asyncio
    return await asyncio.to_thread(_process_recording_sync, ctx, recording_id)


def _process_recording_sync(ctx, recording_id: int):
    """Isi sinkron process_recording. Dipanggil lewat thread executor."""
    logger.info("Memproses rekaman %s", recording_id)

    engine_db = create_engine(DATABASE_URL)
    thresholds = _load_thresholds()

    with Session(engine_db) as session:
        row = session.execute(
            text("SELECT id, storage_key, site_id, status FROM recordings WHERE id = :id"),
            {"id": recording_id},
        ).fetchone()

        if not row:
            logger.error("Rekaman %s tidak ditemukan", recording_id)
            return

        storage_key = row[1]
        site_id = row[2]

        attempt = session.execute(
            text("SELECT attempts FROM jobs WHERE recording_id = :rid ORDER BY id DESC LIMIT 1"),
            {"rid": recording_id},
        ).scalar() or 0

        session.execute(
            text(
                "UPDATE jobs SET status = 'running', started_at = NOW(), "
                "attempts = attempts + 1 WHERE recording_id = :rid"
            ),
            {"rid": recording_id},
        )
        session.execute(
            text("UPDATE recordings SET status = 'processing', error_message = NULL WHERE id = :id"),
            {"id": recording_id},
        )
        session.commit()

        # Session di worker ini sinkron (sqlalchemy.orm.Session), bukan async.
        percobaan = (
            session.execute(
                text("SELECT attempts FROM jobs WHERE recording_id = :rid ORDER BY id DESC LIMIT 1"),
                {"rid": recording_id},
            )
        ).scalar() or 0

        # Progres terakhir disimpan di sini supaya kegagalan bisa menulis stage
        # gagal tanpa mengembalikan angkanya ke nol.
        progres = PROGRES["antre"]
        tulis_progres(session, recording_id, "antre", progres)

        if percobaan >= MAX_ATTEMPTS:
            alasan = (
                f"sudah dicoba {percobaan} kali, batas {MAX_ATTEMPTS}. "
                "Periksa berkasnya lalu unggah ulang."
            )
            session.execute(
                text(
                    "UPDATE jobs SET status = 'failed', last_error = :err, finished_at = NOW() "
                    "WHERE recording_id = :rid"
                ),
                {"err": alasan, "rid": recording_id},
            )
            session.execute(
                text("UPDATE recordings SET status = 'failed', error_message = :err WHERE id = :id"),
                {"err": alasan, "id": recording_id},
            )
            tulis_progres(session, recording_id, "gagal", progres)
            session.commit()
            logger.warning("Rekaman %s dilewati: %s", recording_id, alasan)
            return

        def lapor(tahap: str, angka: int) -> None:
            """Tulis tahap dan progres, sekaligus simpan angka terakhirnya."""
            nonlocal progres
            progres = angka
            tulis_progres(session, recording_id, tahap, angka)

        tmp = tempfile.NamedTemporaryFile(suffix=Path(storage_key).suffix or ".wav", delete=False)
        tmp.close()
        jalur_audio: AudioJalur | None = None

        try:
            lapor("unduh", PROGRES["unduh"])
            with open(tmp.name, "wb") as fh:
                s3.download_fileobj(S3_BUCKET, storage_key, fh)
            logger.info("Rekaman %s terunduh dari storage (%s)", recording_id, storage_key)

            lapor("dekode", PROGRES["dekode"])
            # m4a dan aac dari ponsel dikonversi dulu, kalau tidak inference gagal.
            # Kanal asli tetap disimpan untuk lokalisasi.
            jalur_audio = siapkan_audio_jalur(Path(tmp.name))
            audio = jalur_audio.mono
            logger.info(
                "Rekaman %s: %d kanal, jalur model %s, jalur lokalisasi %s",
                recording_id, jalur_audio.kanal, audio.name,
                jalur_audio.multikanal.name if jalur_audio.multikanal else "tidak ada",
            )

            site_row = session.execute(
                text(
                    "SELECT ST_Y(geom::geometry), ST_X(geom::geometry) FROM sites WHERE id = :id"
                ),
                {"id": site_id},
            ).fetchone()
            lat, lon = (site_row[0], site_row[1]) if site_row else (None, None)

            # Ulang proses (retry) membersihkan hasil lama supaya tidak menumpuk.
            if attempt >= 1:
                session.execute(
                    text(
                        "DELETE FROM detections WHERE recording_id = :rid AND verified_status = 'unverified'"
                    ),
                    {"rid": recording_id},
                )
                session.execute(
                    text("DELETE FROM acoustic_indices WHERE recording_id = :rid"),
                    {"rid": recording_id},
                )
                session.commit()

            lapor("birdnet", PROGRES["birdnet"])
            detections = run_inference(
                str(audio), lat=lat, lon=lon, min_conf=0.1,
                lapor_tahap=lambda tahap, angka: lapor(tahap, angka),
            )
            lapor("birdnet", PROGRES["birdnet_selesai"])
            logger.info("Rekaman %s: %d deteksi (%s)", recording_id, len(detections), _engine_name)

            try:
                import soundfile as sf
                info = sf.info(str(audio))
                session.execute(
                    text(
                        "UPDATE recordings SET duration_s = :dur, sample_rate = :sr WHERE id = :id"
                    ),
                    {"dur": info.duration, "sr": info.samplerate, "id": recording_id},
                )
            except Exception as exc:
                logger.warning("Metadata audio rekaman %s tidak terbaca: %s", recording_id, exc)

            lapor("klasifikasi", PROGRES["klasifikasi"])
            existing = session.execute(
                text("SELECT COUNT(*) FROM detections WHERE recording_id = :rid"),
                {"rid": recording_id},
            ).scalar()

            id_deteksi: list[tuple[int, dict]] = []

            if existing == 0:
                for d in detections:
                    sp = session.execute(
                        text("SELECT id FROM species WHERE scientific_name = :name"),
                        {"name": d["scientific_name"]},
                    ).fetchone()

                    if not sp:
                        session.execute(
                            text(
                                """
                                INSERT INTO species (scientific_name, common_name_en, default_threshold)
                                VALUES (:sci, :en, :thr)
                                ON CONFLICT (scientific_name) DO NOTHING
                                """
                            ),
                            {
                                "sci": d["scientific_name"],
                                "en": d["common_name"],
                                "thr": float(thresholds.get(d["scientific_name"], 0.5)),
                            },
                        )
                        sp = session.execute(
                            text("SELECT id FROM species WHERE scientific_name = :name"),
                            {"name": d["scientific_name"]},
                        ).fetchone()

                    if sp:
                        baris_deteksi = session.execute(
                            text(
                                """
                                INSERT INTO detections
                                    (recording_id, species_id, confidence, start_s, end_s,
                                     engine, engine_version, verified_status)
                                VALUES (:rid, :sid, :conf, :start, :end, :eng, :ver, 'unverified')
                                RETURNING id
                                """
                            ),
                            {
                                "rid": recording_id,
                                "sid": sp[0],
                                "conf": d["confidence"],
                                "start": d["start_s"],
                                "end": d["end_s"],
                                "eng": d["engine"],
                                "ver": d["engine_version"],
                            },
                        ).fetchone()
                        if baris_deteksi:
                            id_deteksi.append((int(baris_deteksi[0]), d))
            else:
                id_deteksi = [
                    (int(r[0]), {"start_s": float(r[1]), "end_s": float(r[2])})
                    for r in session.execute(
                        text(
                            "SELECT id, start_s, end_s FROM detections WHERE recording_id = :rid"
                        ),
                        {"rid": recording_id},
                    ).all()
                ]

            lapor("klasifikasi", PROGRES["klasifikasi_selesai"])
            logger.info("Rekaman %s: %d baris deteksi tersimpan", recording_id, len(id_deteksi))

            # Arah dan jangkauan dihitung dari audio multikanal rekaman ini.
            # Kalau geometri perangkat atau kolomnya tidak ada, kolom deteksi
            # dibiarkan kosong, bukan diisi nol.
            lapor("lokalisasi", PROGRES["lokalisasi"])
            spacing_m, acuan_jarak = baca_acuan_perangkat(session, recording_id)
            jalur_multi = jalur_audio.multikanal
            if jalur_multi is None:
                logger.info(
                    "Rekaman %s: arah tidak dihitung, berkas hanya %d kanal",
                    recording_id, jalur_audio.kanal,
                )
            elif not spacing_m:
                logger.info(
                    "Rekaman %s: arah tidak dihitung, perangkat belum punya mic_spacing_m",
                    recording_id,
                )

            jumlah_arah = terapkan_lokalisasi(
                session, id_deteksi, jalur_multi, jalur_audio.kanal, spacing_m, acuan_jarak
            )
            logger.info(
                "Rekaman %s: %d dari %d deteksi punya arah (%s, %d kanal, jarak antar mic %s m)",
                recording_id, jumlah_arah, len(id_deteksi),
                info_lokalisasi()["engine"], jalur_audio.kanal, spacing_m,
            )

            lapor("indeks", PROGRES["indeks"])
            indices, idx_note = compute_acoustic_indices(str(audio))
            logger.info("Rekaman %s indeks: %s", recording_id, indices)

            existing_idx = session.execute(
                text("SELECT COUNT(*) FROM acoustic_indices WHERE recording_id = :rid"),
                {"rid": recording_id},
            ).scalar()

            if existing_idx == 0:
                session.execute(
                    text(
                        """
                        INSERT INTO acoustic_indices (recording_id, aci, ndsi, adi, bi)
                        VALUES (:rid, :aci, :ndsi, :adi, :bi)
                        """
                    ),
                    {"rid": recording_id, **indices},
                )

            lapor("spektrogram", PROGRES["spektrogram"])
            simpan_spektrogram(audio, storage_key)

            session.execute(
                text("UPDATE recordings SET status = 'done' WHERE id = :id"),
                {"id": recording_id},
            )
            session.execute(
                text(
                    "UPDATE jobs SET status = 'done', finished_at = NOW(), last_error = :note "
                    "WHERE recording_id = :rid"
                ),
                {"rid": recording_id, "note": idx_note},
            )
            session.commit()
            # Peringatan spesies prioritas (blok H). Tidak boleh menggagalkan
            # job; fungsi menangkap semua galatnya sendiri.
            kirim_peringatan_prioritas(session, recording_id)
            lapor("selesai", PROGRES["selesai"])
            logger.info("Rekaman %s selesai diproses", recording_id)

        except Exception as exc:
            logger.error("Rekaman %s gagal: %s", recording_id, exc)
            session.execute(
                text(
                    "UPDATE recordings SET status = 'failed', error_message = :err WHERE id = :id"
                ),
                {"err": str(exc)[:500], "id": recording_id},
            )
            session.execute(
                text(
                    "UPDATE jobs SET status = 'failed', last_error = :err, finished_at = NOW() "
                    "WHERE recording_id = :rid"
                ),
                {"err": str(exc)[:500], "rid": recording_id},
            )
            session.commit()
            # Progres berhenti di angka terakhir, tidak dikembalikan ke nol.
            tulis_progres(session, recording_id, "gagal", progres)
            raise
        finally:
            if jalur_audio is not None:
                jalur_audio.bersihkan()
            if os.path.exists(tmp.name):
                os.unlink(tmp.name)


def kirim_peringatan_prioritas(session: Session, recording_id: int) -> None:
    """Kirim satu email ke admin/peneliti kalau rekaman memuat spesies prioritas.

    Semua galat ditangkap di sini supaya peringatan tidak pernah menggagalkan
    job pemrosesan. Rekaman akun tamu tidak memicu peringatan. Paling banyak
    satu email per spesies per lokasi per JEDA_PERINGATAN_JAM jam (lewat Redis).
    """
    try:
        baris = session.execute(
            text(
                "SELECT r.site_id, u.email FROM recordings r "
                "JOIN users u ON u.id = r.uploaded_by WHERE r.id = :rid"
            ),
            {"rid": recording_id},
        ).fetchone()
        if not baris:
            return
        site_id, uploader_email = baris
        if uploader_email and uploader_email.endswith("@tamu.gemahutan.invalid"):
            return

        deteksi = session.execute(
            text(
                """
                SELECT s.scientific_name, s.common_name_id, d.confidence, d.start_s
                FROM detections d
                JOIN species s ON s.id = d.species_id
                WHERE d.recording_id = :rid AND s.prioritas = true
                  AND d.confidence >= COALESCE(s.default_threshold, 0.5)
                ORDER BY d.confidence DESC
                """
            ),
            {"rid": recording_id},
        ).fetchall()
        if not deteksi:
            return

        # Rate limit per spesies per lokasi. Kalau Redis tidak bisa dipakai,
        # lanjut tanpa pembatas supaya peringatan tidak hilang diam-diam.
        kirim = list(deteksi)
        try:
            import redis

            r = redis.from_url(REDIS_URL, decode_responses=True)
            belum_kirim = []
            for d in deteksi:
                kunci = f"gemahutan:peringatan:{site_id}:{d[0]}"
                if r.set(kunci, "1", nx=True, ex=JEDA_PERINGATAN_JAM * 3600):
                    belum_kirim.append(d)
            if not belum_kirim:
                return
            kirim = belum_kirim
        except Exception as exc:  # noqa: BLE001
            logger.warning("Pembatas jeda peringatan gagal, lanjut kirim: %s", exc)

        penerima = [
            row[0]
            for row in session.execute(
                text(
                    "SELECT email FROM users WHERE role IN ('admin','researcher') "
                    "AND is_active = true"
                )
            ).fetchall()
        ]
        if not penerima:
            return

        if not (SMTP_HOST and SMTP_USER and SMTP_APP_PASSWORD):
            logger.warning(
                "Peringatan spesies prioritas rekaman %s tidak terkirim: SMTP belum dikonfigurasi",
                recording_id,
            )
            return

        nama_situs = (
            session.execute(text("SELECT name FROM sites WHERE id = :sid"), {"sid": site_id}).scalar()
            or "?"
        )
        baris_spesies = "\n".join(
            f"- {d[1] or d[0]} ({d[0]}): skor {d[2]:.2f}, mulai {d[3]:.1f} detik"
            for d in kirim
        )
        isi = (
            "GemaHutan mendeteksi spesies prioritas di rekaman baru.\n\n"
            f"Lokasi: {nama_situs}\n"
            f"Rekaman: {recording_id}\n\n"
            f"{baris_spesies}\n\n"
            "Buka aplikasi untuk melihat detailnya."
        )

        pesan = EmailMessage()
        pesan["Subject"] = "[GemaHutan] Spesies prioritas terdeteksi"
        pesan["From"] = SMTP_FROM
        pesan["To"] = ", ".join(penerima)
        pesan.set_content(isi)
        with smtplib.SMTP(SMTP_HOST, SMTP_PORT, timeout=30) as smtp:
            smtp.starttls()
            smtp.login(SMTP_USER, SMTP_APP_PASSWORD)
            smtp.send_message(pesan)
        logger.info("Peringatan spesies prioritas terkirim untuk rekaman %s", recording_id)
    except Exception as exc:  # noqa: BLE001
        logger.error(
            "Gagal kirim peringatan spesies prioritas untuk rekaman %s: %s",
            recording_id,
            exc,
        )


async def startup(ctx):
    get_engine()
    await write_heartbeat(ctx)


async def shutdown(ctx):
    pass


class WorkerSettings:
    functions = [process_recording, sweep_stuck_jobs, write_heartbeat]
    cron_jobs = [
        cron(write_heartbeat, second={0, 30}, run_at_startup=True),
        cron(sweep_stuck_jobs, second={20, 50}),
    ]
    on_startup = startup
    on_shutdown = shutdown
    redis_settings = RedisSettings.from_dsn(REDIS_URL)
    max_jobs = 2
    job_timeout = 900
    max_tries = 3
    health_check_interval = 30
