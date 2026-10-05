import enum
from datetime import datetime

from geoalchemy2 import Geometry
from sqlalchemy import (
    Boolean,
    DateTime,
    Enum,
    Float,
    ForeignKey,
    Index,
    Integer,
    String,
    Text,
    func,
)
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.models.base import Base


class UserRole(str, enum.Enum):
    ranger = "ranger"
    researcher = "researcher"
    admin = "admin"


class RecordingStatus(str, enum.Enum):
    pending = "pending"
    processing = "processing"
    done = "done"
    failed = "failed"


class DeviceType(str, enum.Enum):
    audiomoth = "audiomoth"
    phone = "phone"
    other = "other"


class VerifiedStatus(str, enum.Enum):
    unverified = "unverified"
    correct = "correct"
    incorrect = "incorrect"
    uncertain = "uncertain"


class JobStatus(str, enum.Enum):
    pending = "pending"
    running = "running"
    done = "done"
    failed = "failed"


class User(Base):
    __tablename__ = "users"

    id: Mapped[int] = mapped_column(primary_key=True)
    email: Mapped[str] = mapped_column(String(255), unique=True, index=True)
    password_hash: Mapped[str] = mapped_column(String(255))
    name: Mapped[str | None] = mapped_column(String(255), nullable=True)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True)
    role: Mapped[UserRole] = mapped_column(
        Enum(UserRole, name="user_role"), default=UserRole.ranger
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now()
    )
    # Nomor versi token. Naik satu setiap kali sandi diatur ulang, dan token yang
    # membawa versi lama langsung ditolak. Dipilih ketimbang menyimpan waktu
    # karena `iat` pada JWT hanya bersatuan detik, sehingga membandingkan waktu
    # memaksa adanya toleransi, dan toleransi itu justru meloloskan sesi lama
    # kalau pengaturan ulang terjadi cepat.
    token_version: Mapped[int] = mapped_column(Integer, default=0, server_default="0")

    sites = relationship("Site", back_populates="owner")
    recordings = relationship("Recording", back_populates="uploaded_by_user")


class Site(Base):
    __tablename__ = "sites"

    id: Mapped[int] = mapped_column(primary_key=True)
    name: Mapped[str] = mapped_column(String(255))
    geom = mapped_column(Geometry("POINT", srid=4326), nullable=True)
    habitat_type: Mapped[str | None] = mapped_column(String(100), nullable=True)
    location: Mapped[str | None] = mapped_column(String(255), nullable=True)
    elevation_m: Mapped[float | None] = mapped_column(Float, nullable=True)
    description: Mapped[str | None] = mapped_column(Text, nullable=True)
    notes: Mapped[str | None] = mapped_column(Text, nullable=True)
    owner_id: Mapped[int] = mapped_column(ForeignKey("users.id"))
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now()
    )
    # Lokasi sistem untuk halaman depan "Coba contoh". Hanya terlihat akun tamu;
    # peran petugas tidak melihatnya di daftar, peta, laporan, maupun pilihan unggah.
    khusus_tamu: Mapped[bool] = mapped_column(Boolean, default=False, server_default="false")

    owner = relationship("User", back_populates="sites")
    devices = relationship("Device", back_populates="site")
    recordings = relationship("Recording", back_populates="site")


class Device(Base):
    __tablename__ = "devices"

    id: Mapped[int] = mapped_column(primary_key=True)
    name: Mapped[str] = mapped_column(String(255))
    type: Mapped[DeviceType] = mapped_column(
        Enum(DeviceType, name="device_type"), default=DeviceType.phone
    )
    site_id: Mapped[int] = mapped_column(ForeignKey("sites.id"))
    serial: Mapped[str | None] = mapped_column(String(120), nullable=True)
    channel_count: Mapped[int] = mapped_column(Integer, default=1)
    mic_spacing_m: Mapped[float | None] = mapped_column(Float, nullable=True)
    reference_distance_m: Mapped[float | None] = mapped_column(Float, nullable=True)
    reference_level_db: Mapped[float | None] = mapped_column(Float, nullable=True)
    installed_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True
    )
    active: Mapped[bool] = mapped_column(Boolean, default=True)
    notes: Mapped[str | None] = mapped_column(Text, nullable=True)

    site = relationship("Site", back_populates="devices")


class Species(Base):
    __tablename__ = "species"

    id: Mapped[int] = mapped_column(primary_key=True)
    scientific_name: Mapped[str] = mapped_column(String(255), unique=True, index=True)
    common_name_id: Mapped[str | None] = mapped_column(String(255), nullable=True)
    common_name_en: Mapped[str | None] = mapped_column(String(255), nullable=True)
    iucn_status: Mapped[str | None] = mapped_column(String(20), nullable=True)
    ebird_code: Mapped[str | None] = mapped_column(String(20), nullable=True)
    default_threshold: Mapped[float] = mapped_column(Float, default=0.5)
    model_supported: Mapped[bool] = mapped_column(Boolean, default=False)
    # Spesies prioritas konservasi: IUCN CR/EN/VU atau Permen LHK P.106/2018,
    # atau ditandai admin. Lokasi tepat deteksinya dirahasiakan untuk peran
    # selain admin dan peneliti.
    prioritas: Mapped[bool] = mapped_column(Boolean, default=False, server_default="false")
    sumber_prioritas: Mapped[str | None] = mapped_column(String(20), nullable=True)


class Recording(Base):
    __tablename__ = "recordings"

    id: Mapped[int] = mapped_column(primary_key=True)
    site_id: Mapped[int] = mapped_column(ForeignKey("sites.id"), index=True)
    device_id: Mapped[int | None] = mapped_column(
        ForeignKey("devices.id"), nullable=True
    )
    uploaded_by: Mapped[int] = mapped_column(ForeignKey("users.id"))
    storage_key: Mapped[str] = mapped_column(String(500))
    original_filename: Mapped[str | None] = mapped_column(String(255), nullable=True)
    batch_id: Mapped[str | None] = mapped_column(String(64), nullable=True, index=True)
    duration_s: Mapped[float | None] = mapped_column(Float, nullable=True)
    sample_rate: Mapped[int | None] = mapped_column(Integer, nullable=True)
    recorded_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True, index=True
    )
    status: Mapped[RecordingStatus] = mapped_column(
        Enum(RecordingStatus, name="recording_status"),
        default=RecordingStatus.pending,
        index=True,
    )
    error_message: Mapped[str | None] = mapped_column(Text, nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now()
    )

    site = relationship("Site", back_populates="recordings")
    uploaded_by_user = relationship("User", back_populates="recordings")
    detections = relationship("Detection", back_populates="recording")
    acoustic_indices = relationship("AcousticIndex", back_populates="recording")
    job = relationship("Job", back_populates="recording", uselist=False)


class Detection(Base):
    __tablename__ = "detections"
    __table_args__ = (
        Index("ix_detections_recording_id", "recording_id"),
        Index("ix_detections_species_confidence", "species_id", "confidence"),
    )

    id: Mapped[int] = mapped_column(primary_key=True)
    recording_id: Mapped[int] = mapped_column(ForeignKey("recordings.id"))
    species_id: Mapped[int] = mapped_column(ForeignKey("species.id"))
    confidence: Mapped[float] = mapped_column(Float)
    start_s: Mapped[float] = mapped_column(Float)
    end_s: Mapped[float] = mapped_column(Float)
    engine: Mapped[str] = mapped_column(String(100))
    engine_version: Mapped[str] = mapped_column(String(50))
    verified_status: Mapped[VerifiedStatus] = mapped_column(
        Enum(VerifiedStatus, name="verified_status"),
        default=VerifiedStatus.unverified,
    )
    verified_by: Mapped[int | None] = mapped_column(
        ForeignKey("users.id"), nullable=True
    )
    verified_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True
    )
    # Hasil lokalisasi. Null berarti belum dihitung atau tidak tersedia, dan
    # tidak diisi nol palsu supaya klien bisa membedakan "tidak ada" dari 0 derajat.
    azimuth_deg: Mapped[float | None] = mapped_column(Float, nullable=True)
    azimuth_confidence: Mapped[float | None] = mapped_column(Float, nullable=True)
    # Sudut cermin yang sama-sama cocok pada susunan mikrofon segaris.
    azimuth_kembar_deg: Mapped[float | None] = mapped_column(Float, nullable=True)
    range_m: Mapped[float | None] = mapped_column(Float, nullable=True)
    localization_engine: Mapped[str | None] = mapped_column(String(50), nullable=True)

    recording = relationship("Recording", back_populates="detections")
    species = relationship("Species")


class AcousticIndex(Base):
    __tablename__ = "acoustic_indices"

    id: Mapped[int] = mapped_column(primary_key=True)
    recording_id: Mapped[int] = mapped_column(
        ForeignKey("recordings.id"), unique=True
    )
    aci: Mapped[float | None] = mapped_column(Float, nullable=True)
    ndsi: Mapped[float | None] = mapped_column(Float, nullable=True)
    adi: Mapped[float | None] = mapped_column(Float, nullable=True)
    bi: Mapped[float | None] = mapped_column(Float, nullable=True)
    computed_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now()
    )

    recording = relationship("Recording", back_populates="acoustic_indices")


class Job(Base):
    __tablename__ = "jobs"

    id: Mapped[int] = mapped_column(primary_key=True)
    recording_id: Mapped[int] = mapped_column(
        ForeignKey("recordings.id"), unique=True
    )
    status: Mapped[JobStatus] = mapped_column(
        Enum(JobStatus, name="job_status"), default=JobStatus.pending
    )
    # Progres 0 sampai 100 dan tahap berjalan. Worker memperbarui keduanya
    # setelah tiap tahap, dan API hanya melaporkan apa yang tertulis di sini.
    progress: Mapped[int] = mapped_column(Integer, default=0)
    stage: Mapped[str | None] = mapped_column(String(50), nullable=True)
    attempts: Mapped[int] = mapped_column(Integer, default=0)
    last_error: Mapped[str | None] = mapped_column(Text, nullable=True)
    started_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True
    )
    finished_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True
    )

    recording = relationship("Recording", back_populates="job")


class AuditLog(Base):
    """Jejak tindakan yang mengubah data atau memberi akses.

    Kenapa aktor disimpan dua kali, id dan email: tabel ini harus tetap terbaca
    setelah akunnya dihapus, dan itu justru keadaan yang paling perlu ditelusuri.
    Kalau hanya id yang disimpan, barisnya jadi yatim dan tidak bisa dibaca lagi.
    Karena itu actor_id sengaja TIDAK memakai ondelete cascade, dan actor_email
    disalin apa adanya saat pencatatan.

    Detail disimpan sebagai JSONB supaya bentuk tiap tindakan berbeda tanpa perlu
    menambah kolom, dan tetap bisa dicari lewat operator JSON Postgres.
    """

    __tablename__ = "audit_logs"

    id: Mapped[int] = mapped_column(primary_key=True)
    actor_id: Mapped[int | None] = mapped_column(
        ForeignKey("users.id", ondelete="SET NULL"), nullable=True, index=True
    )
    actor_email: Mapped[str | None] = mapped_column(String(255), nullable=True)
    # Nama tindakan dalam bentuk titik, misal "detection.verify" atau "user.role_change".
    action: Mapped[str] = mapped_column(String(60), index=True)
    entity_type: Mapped[str | None] = mapped_column(String(40), nullable=True)
    entity_id: Mapped[str | None] = mapped_column(String(60), nullable=True)
    detail: Mapped[dict | None] = mapped_column(JSONB, nullable=True)
    # Alamat pengirim disimpan karena tindakan yang sama dari alamat berbeda
    # punya arti berbeda saat ditelusuri.
    ip: Mapped[str | None] = mapped_column(String(60), nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), index=True
    )


Index("ix_audit_logs_entity", AuditLog.entity_type, AuditLog.entity_id)


class PasswordResetToken(Base):
    """Token sekali pakai untuk mengatur ulang sandi.

    Dua pilihan yang penting untuk keamanan:

    1. Yang disimpan adalah HASH token, bukan tokennya. Alasannya sama seperti
       sandi: kalau isi tabel ini bocor, token mentahnya tidak bisa dipakai untuk
       membajak akun. Token dikirim ke pengguna lewat email, dan hash-nya yang
       ditahan di sini.

    2. Barisnya tidak dihapus setelah dipakai, melainkan ditandai `used_at`. Jejak
       token yang pernah dipakai ikut terpakai saat menelusuri masalah, dan
       penghapusan baris justru menghilangkan buktinya.

    Token kedaluwarsa tidak perlu dibersihkan untuk keamanan karena
    `expires_at`-nya diperiksa saat verifikasi; pembersihan hanya soal ukuran.
    """

    __tablename__ = "password_reset_tokens"

    id: Mapped[int] = mapped_column(primary_key=True)
    # CASCADE, berbeda dari audit_logs yang memakai SET NULL. Alasannya beda
    # maksud: token atur ulang itu sementara dan tidak punya nilai sebagai bukti
    # setelah akunnya dihapus, sedangkan baris audit justru harus bertahan.
    # Tanpa CASCADE, penghapusan pengguna gagal karena baris token menahannya.
    user_id: Mapped[int] = mapped_column(
        ForeignKey("users.id", ondelete="CASCADE"), index=True
    )
    # SHA-256 heksadesimal selalu 64 karakter.
    token_hash: Mapped[str] = mapped_column(String(64), unique=True, index=True)
    expires_at: Mapped[datetime] = mapped_column(DateTime(timezone=True))
    used_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    # Alamat dari mana permintaan datang, untuk menelusuri penyalahgunaan.
    requested_ip: Mapped[str | None] = mapped_column(String(60), nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now()
    )

    user = relationship("User")
