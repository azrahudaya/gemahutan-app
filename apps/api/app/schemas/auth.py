from pydantic import BaseModel, EmailStr, Field, field_validator, model_validator

# Sandi yang paling sering dipakai. Daftarnya pendek dan sengaja tidak lengkap:
# tujuannya menahan pilihan yang jelas buruk, bukan menggantikan pemeriksa
# kebocoran sandi. Sisanya ditutup panjang minimal dan syarat ragam karakter.
SANDI_UMUM = {
    "password", "password1", "password123", "passw0rd", "12345678", "123456789",
    "1234567890", "qwertyuiop", "qwerty123", "iloveyou", "admin123", "administrator",
    "letmein123", "welcome123", "abc12345", "monkey123", "dragon123", "sunshine1",
    "princess1", "football1", "baseball1", "gemahutan", "gemahutan1", "indonesia1",
    "rahasia123", "semangat1", "bismillah1", "kucing123", "sayang123", "cinta123",
    "burung123",
}

PESAN_SANDI = (
    "Sandi minimal 8 karakter, memuat huruf dan angka, tidak memakai sandi umum, "
    "dan tidak memuat bagian email kamu."
)


def periksa_kekuatan_sandi(sandi: str, email: str | None = None) -> str:
    """Periksa kekuatan sandi, kembalikan sandi kalau lolos.

    Dipakai skema daftar akun, dan bisa dipakai ulang jalur ganti sandi nanti,
    supaya aturannya cuma ada di satu tempat.
    """
    if len(sandi) < 8:
        raise ValueError(PESAN_SANDI)
    if not any(c.isalpha() for c in sandi) or not any(c.isdigit() for c in sandi):
        raise ValueError(PESAN_SANDI)
    if sandi.lower() in SANDI_UMUM:
        raise ValueError(PESAN_SANDI)
    if email:
        bagian = email.split("@")[0].lower()
        # Bagian email harus panjang minimal 4 huruf supaya tidak menolak sandi
        # normal hanya karena kebetulan memuat dua atau tiga huruf pendek.
        if len(bagian) >= 4 and bagian in sandi.lower():
            raise ValueError(PESAN_SANDI)
    return sandi


class RegisterRequest(BaseModel):
    email: EmailStr
    password: str = Field(min_length=8, max_length=128)
    # Nama tampilan dikirim halaman daftar. Sebelumnya dibuang diam-diam.
    name: str | None = None

    @field_validator("password")
    @classmethod
    def _kekuatan_sandi(cls, v: str) -> str:
        return periksa_kekuatan_sandi(v)

    @model_validator(mode="after")
    def _sandi_bukan_email(self) -> "RegisterRequest":
        # Pemeriksaan silang lapangan: sandi tidak boleh memuat email pendaftarnya.
        periksa_kekuatan_sandi(self.password, self.email)
        return self


class ForgotPasswordRequest(BaseModel):
    email: EmailStr


class ResetPasswordRequest(BaseModel):
    # Batas bawah 10 supaya token kosong atau terpotong ditolak lebih awal,
    # sebelum menyentuh basis data.
    token: str = Field(min_length=10, max_length=200)
    password: str = Field(min_length=8, max_length=128)

    @field_validator("password")
    @classmethod
    def _kekuatan_sandi(cls, v: str) -> str:
        # Kebijakan yang sama dengan pendaftaran. Tanpa ini, sandi lemah bisa
        # masuk lewat jalur pemulihan walau sudah diblokir di jalur daftar.
        return periksa_kekuatan_sandi(v)


class ActivateAccountRequest(BaseModel):
    """Token undangan + sandi baru untuk mengaktifkan akun yang diundang."""

    token: str = Field(min_length=10, max_length=200)
    password: str = Field(min_length=8, max_length=128)

    @field_validator("password")
    @classmethod
    def _kekuatan_sandi(cls, v: str) -> str:
        return periksa_kekuatan_sandi(v)


class LoginRequest(BaseModel):
    email: EmailStr
    password: str


class TokenResponse(BaseModel):
    access_token: str
    refresh_token: str
    token_type: str = "bearer"


class RefreshRequest(BaseModel):
    refresh_token: str


class LogoutRequest(BaseModel):
    # Opsional: kalau dikirim, refresh token ikut dicabut.
    refresh_token: str | None = None


class UserResponse(BaseModel):
    id: int
    email: str
    role: str
    created_at: str

    model_config = {"from_attributes": True}
