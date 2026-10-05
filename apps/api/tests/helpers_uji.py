"""Pembantu test Fase 2: berkas audio buatan, login, dan unggah rekaman."""
import io
import struct
import uuid
import wave


def wav_senyap(detik: float = 0.4, sr: int = 8000) -> bytes:
    """WAV mono berisi keheningan, dibuat di memori untuk uji unggah."""
    buf = io.BytesIO()
    with wave.open(buf, "wb") as w:
        w.setnchannels(1)
        w.setsampwidth(2)
        w.setframerate(sr)
        jumlah = int(sr * detik)
        w.writeframes(struct.pack(f"<{jumlah}h", *([0] * jumlah)))
    return buf.getvalue()


async def login(client, email: str, password: str) -> dict:
    resp = await client.post("/api/v1/auth/login", json={"email": email, "password": password})
    assert resp.status_code == 200, resp.text
    return {"Authorization": f"Bearer {resp.json()['access_token']}"}


async def admin(client) -> dict:
    return await login(client, "admin@gemahutan.id", "admin123")


async def ranger_baru(client) -> tuple[dict, int]:
    """Daftar akun baru dengan peran bawaan, kembalikan header dan id-nya."""
    email = f"fase2-{uuid.uuid4().hex[:8]}@gemahutan.id"
    daftar = await client.post(
        "/api/v1/auth/register",
        json={"email": email, "password": "testpass123", "name": "Uji Fase 2"},
    )
    assert daftar.status_code == 201, daftar.text
    return await login(client, email, "testpass123"), daftar.json()["id"]


async def lokasi_pertama(client, headers: dict) -> int:
    resp = await client.get("/api/v1/sites", headers=headers)
    assert resp.status_code == 200 and resp.json(), "butuh minimal satu lokasi"
    return resp.json()[0]["id"]


async def unggah(client, headers: dict, site_id: int, device_id: int | None = None) -> dict:
    data = {"site_id": str(site_id)}
    if device_id is not None:
        data["device_id"] = str(device_id)
    resp = await client.post(
        "/api/v1/recordings",
        headers=headers,
        files={"file": ("uji-fase2.wav", wav_senyap(), "audio/wav")},
        data=data,
    )
    assert resp.status_code in (201, 202), resp.text
    return resp.json()


async def unggah_mentah(client, headers: dict, site_id: int):
    """Unggah tanpa assert status, kembalikan Response (untuk uji 429/kuota)."""
    return await client.post(
        "/api/v1/recordings",
        headers=headers,
        files={"file": ("uji-fase2.wav", wav_senyap(), "audio/wav")},
        data={"site_id": str(site_id)},
    )
