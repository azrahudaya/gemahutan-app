from functools import lru_cache

from pydantic import Field, model_validator
from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    # App
    app_name: str = "GemaHutan API"
    app_version: str = "0.1.0"
    debug: bool = False
    # "production" mengaktifkan pemeriksaan konfigurasi saat start dan mematikan
    # dokumentasi API otomatis kecuali ENABLE_DOCS=true.
    environment: str = "development"
    enable_docs: bool = True
    # Pendaftaran akun baru. Di produksi biasanya dimatikan supaya hanya petugas
    # terdaftar yang bisa masuk dan mengubah data.
    allow_registration: bool = True

    # Auth
    secret_key: str = "change-me-in-production"
    jwt_secret: str = "change-me-in-production"
    jwt_algorithm: str = "HS256"
    jwt_access_token_expire_minutes: int = 30
    jwt_refresh_token_expire_days: int = 7

    # Database
    database_url: str = "postgresql+asyncpg://gemahutan:gemahutan@db:5432/gemahutan"
    database_url_sync: str = "postgresql://gemahutan:gemahutan@db:5432/gemahutan"

    # Redis
    redis_url: str = "redis://redis:6379/0"
    # Pembatas laju umum per IP dan kelas operasi. Bisa dimatikan kalau ada
    # pengujian beban atau saat aplikasi dijalankan di belakang proxy yang
    # menggabungkan banyak pengguna ke satu alamat IP.
    rate_limit_enabled: bool = True

    # Akun tamu untuk halaman depan publik. Akun dibuat lewat /api/v1/auth/tamu yang
    # hanya menerima permintaan dari server web (membawa TAMU_RAHASIA), dibatasi per
    # IP pengunjung, dan dibersihkan setelah TAMU_UMUR_JAM.
    tamu_aktif: bool = False
    tamu_rahasia: str = ""
    tamu_batas_per_jam: int = 30
    tamu_umur_jam: int = 24
    tamu_batas_unggah_per_hari: int = 10

    # Pengiriman email. Sumbernya /etc/gemahutan/notif.env (SMTP_USER dan
    # SMTP_APP_PASSWORD), berkas yang sama dipakai notifikasi server. Host dan
    # port Gmail sudah jadi nilai bawaan. Selama SMTP_USER kosong, tautan atur
    # ulang sandi hanya ditulis ke log di luar produksi, dan pengirimannya
    # dilaporkan gagal di produksi. Tidak ada tautan yang bocor ke log produksi.
    smtp_host: str = "smtp.gmail.com"
    smtp_port: int = 587
    smtp_user: str = ""
    smtp_password: str = Field(default="", validation_alias="SMTP_APP_PASSWORD")
    smtp_from: str = ""
    smtp_starttls: bool = True

    @model_validator(mode="after")
    def _smtp_from_bawaan(self) -> "Settings":
        # Gmail memakai alamat akun sebagai pengirim. Kalau SMTP_FROM tidak
        # diisi, pakai alamat SMTP_USER.
        if not self.smtp_from:
            self.smtp_from = self.smtp_user
        return self

    # Alamat halaman depan, dipakai menyusun tautan atur ulang sandi di email.
    frontend_url: str = "http://localhost:3001"
    # Masa berlaku token atur ulang. 30 menit cukup untuk membuka email, dan
    # tidak terlalu lama kalau emailnya sudah terlanjur bocor.
    reset_token_minutes: int = 30
    # Masa berlaku token undangan akun. Lebih panjang karena undangan dibuka
    # saat petugas sempat, bukan saat sedang lupa sandi.
    invite_token_hours: int = 72

    # S3 / MinIO
    s3_endpoint: str = "http://minio:9000"
    s3_access_key: str = "minioadmin"
    s3_secret_key: str = "minioadmin"
    s3_bucket: str = "gemahutan-audio"
    s3_region: str = "us-east-1"

    # Inference
    inference_engine: str = "birdnet"

    # CORS
    cors_origins: str = "http://localhost:3000,http://localhost:8000"

    model_config = {"env_file": ".env", "env_file_encoding": "utf-8", "extra": "ignore"}

    def production_problems(self) -> list[str]:
        """Daftar konfigurasi berbahaya yang masih dipakai di produksi.

        Dipakai saat start: aplikasi menolak jalan di produksi kalau rahasia
        masih nilai contoh, karena token bisa dipalsukan oleh siapa pun.
        """
        problems = []
        default_secrets = {"change-me-in-production", "test-secret", "secret", ""}
        if self.jwt_secret in default_secrets:
            problems.append("JWT_SECRET masih nilai contoh")
        if self.secret_key in default_secrets:
            problems.append("SECRET_KEY masih nilai contoh")
        if self.s3_access_key == "minioadmin" or self.s3_secret_key == "minioadmin":
            problems.append("kredensial MinIO masih minioadmin")
        if "*" in self.cors_origins or "localhost" in self.cors_origins:
            problems.append("CORS_ORIGINS masih menyertakan localhost atau wildcard")
        return problems


@lru_cache
def get_settings() -> Settings:
    return Settings()
