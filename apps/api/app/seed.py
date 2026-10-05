"""Seed database dengan spesies burung Indonesia, lokasi, dan akun dasar.

Sifat wajib: idempoten. Menjalankan berkas ini dua kali berturut tidak boleh
menambah baris baru. Karena itu tidak ada lagi pemeriksaan "sudah pernah diisi
lalu berhenti"; setiap baris dicocokkan dulu berdasarkan kunci alaminya:

- pengguna  : email
- spesies   : scientific_name
- lokasi    : name
- perangkat : name di dalam satu lokasi

Daftar spesies yang diisi adalah gabungan dua sumber:
1. SPECIES_DATA di berkas ini, daftar kurasi dengan status IUCN dan kode eBird.
2. ml/data/species_list.json, 25 spesies yang benar-benar dikenal classifier
   Track B. Spesies dari sumber kedua ditandai model_supported = true.

Baris spesies yang tidak ada di kedua daftar itu dan tidak dipakai deteksi mana
pun akan dihapus, karena tidak bisa muncul di aplikasi dan hanya menambah
kebisingan di halaman Spesies. Spesies yang masih dipakai deteksi selalu
disimpan walau tidak ada di daftar, supaya riwayat deteksi tidak ikut hilang.

Jalankan: docker compose exec api python -m app.seed
"""
import asyncio
import json
import os
from pathlib import Path

from passlib.hash import argon2
from sqlalchemy import select

from app.database import async_session_factory
from app.models.tables import Detection, Device, DeviceType, Site, Species, User, UserRole

SPECIES_DATA = [
    ("Acridotheres javanicus", "Kerak Kerbau", "Javan Myna", "LC", "javmyn1", 0.5),
    ("Aegithina tiphia", "Cipoh Kacat", "Common Iora", "LC", "comioa1", 0.5),
    ("Aethopyga mystacalis", "Burung Madu Kumis", "Javan Sunbird", "LC", "javsun2", 0.5),
    ("Alcedo meninting", "Raja Udang Meninting", "Blue-eared Kingfisher", "LC", "blekin1", 0.5),
    ("Anthreptes malacensis", "Madu Kelapa", "Plain-throated Sunbird", "LC", "brtsun1", 0.5),
    ("Arachnothera longirostra", "Pijantung Kecil", "Little Spiderhunter", "LC", "litspi1", 0.5),
    ("Centropus sinensis", "Bubut Besar", "Greater Coucal", "LC", "grecou1", 0.5),
    ("Chalcophaps indica", "Delimukan Zamrud", "Asian Emerald Dove", "LC", "emedog1", 0.5),
    ("Cinnyris jugularis", "Madu Sriganti", "Olive-backed Sunbird", "LC", "olbsun3", 0.5),
    ("Collocalia linchi", "Walet Linci", "Cave Swiftlet", "LC", "cavswi1", 0.5),
    ("Dicaeum trochileum", "Cabai Jawa", "Scarlet-headed Flowerpecker", "LC", "schflo1", 0.5),
    ("Geopelia striata", "Perkutut Jawa", "Zebra Dove", "LC", "zebdov", 0.5),
    ("Halcyon cyanoventris", "Cekakak Jawa", "Javan Kingfisher", "LC", "javkin1", 0.5),
    ("Hemipus hirundinaceus", "Jingjing Batu", "Black-winged Flycatcher-shrike", "LC", "bkwfly1", 0.5),
    ("Lonchura leucogastroides", "Bondol Jawa", "Javan Munia", "LC", "javmun1", 0.5),
    ("Lonchura maja", "Bondol Haji", "White-headed Munia", "LC", "whhmun1", 0.5),
    ("Megalaima armillaris", "Takur Tukang", "Flame-fronted Barbet", "NT", "flfbar1", 0.45),
    ("Megalaima javensis", "Takur Tohtor", "Black-banded Barbet", "NT", "blbbar2", 0.45),
    ("Orthotomus sutorius", "Cinenen Pisang", "Common Tailorbird", "LC", "comtai1", 0.5),
    ("Pericrocotus cinnamomeus", "Sepah Kecil", "Small Minivet", "LC", "smmini1", 0.5),
    ("Prinia familiaris", "Perenjak Jawa", "Bar-winged Prinia", "LC", "bawpri1", 0.5),
    ("Pycnonotus aurigaster", "Cucak Kutilang", "Sooty-headed Bulbul", "LC", "sohbul1", 0.5),
    ("Pycnonotus goiavier", "Merbah Cerukcuk", "Yellow-vented Bulbul", "LC", "yevbul2", 0.5),
    ("Spilopelia chinensis", "Tekukur Biasa", "Spotted Dove", "LC", "spodov", 0.5),
    ("Streptopelia bitorquata", "Dederuk Jawa", "Island Collared-Dove", "LC", "iscdov1", 0.5),
    ("Treron griseicauda", "Punai Penganten", "Grey-cheeked Green-Pigeon", "LC", "gycgpi1", 0.5),
    ("Zosterops palpebrosus", "Kacamata Biasa", "Indian White-eye", "LC", "inswhe1", 0.5),
    ("Nisaetus bartelsi", "Elang Jawa", "Javan Hawk-Eagle", "EN", "javhae1", 0.35),
    ("Ketupa ketupu", "Beluk Ketupa", "Buffy Fish-Owl", "LC", "buffis1", 0.45),
    ("Leptocoma sperata", "Madu Bakau", "Purple-throated Sunbird", "LC", "putsun2", 0.5),
    # Lima spesies ini dikenal classifier Track B tetapi belum ada di seed,
    # jadi daftar spesies aplikasi tidak cocok dengan kemampuan model.
    ("Centropus bengalensis", "Bubut Alang-alang", "Lesser Coucal", "LC", "lescou1", 0.5),
    ("Cisticola juncidis", "Cici Padi", "Zitting Cisticola", "LC", "zcicis1", 0.5),
    ("Dicrurus macrocercus", "Srigunting Hitam", "Black Drongo", "LC", "bladro1", 0.5),
    ("Haliastur indus", "Elang Bondol", "Brahminy Kite", "LC", "brakit1", 0.5),
    ("Todiramphus chloris", "Cekakak Sungai", "Collared Kingfisher", "LC", "colkin1", 0.5),
]

SITES_DATA = [
    ("Taman Nasional Gunung Halimun Salak", -6.7394, 106.5497, "tropical_rainforest"),
    ("Taman Nasional Ujung Kulon", -6.7583, 105.3259, "lowland_forest"),
    ("Taman Nasional Gunung Gede Pangrango", -6.7875, 106.9839, "montane_forest"),
    ("Taman Nasional Alas Purwo", -8.6333, 114.3667, "lowland_forest"),
    ("Taman Nasional Baluran", -7.8500, 114.3667, "savanna_woodland"),
    ("Cagar Alam Pulau Sempu", -8.4500, 112.6833, "coastal_forest"),
]

def _akar_repo() -> Path:
    """Folder yang memuat ml/. Di host: akar repo. Di image api: /app."""
    berkas = Path(__file__).resolve()
    for basis in berkas.parents:
        if (basis / "ml").is_dir():
            return basis
    return berkas.parents[-1]


ROOT = _akar_repo()

# ml/ ada di dalam image api pada /app/ml lewat variabel ML_DIR. Kalau variabel
# itu tidak diset, jalur relatif dari akar repo yang dipakai.
ML_DIR = Path(os.getenv("ML_DIR") or (ROOT / "ml"))


def _baca_json(relatif: str) -> object | None:
    """Baca berkas JSON relatif terhadap folder ml/."""
    for basis in (ML_DIR, ROOT / "ml"):
        try:
            return json.loads((basis / relatif).read_text())
        except Exception:
            continue
    return None


def _daftar_model() -> dict[str, dict]:
    """25 spesies di ml/data/species_list.json, dikunci scientific_name."""
    data = _baca_json("data/species_list.json")
    if not isinstance(data, list):
        return {}
    hasil = {}
    for baris in data:
        if isinstance(baris, dict) and baris.get("scientific_name"):
            hasil[baris["scientific_name"]] = baris
    return hasil


def _baca_ambang_terkalibrasi() -> dict:
    """Ambang per spesies dari ml/reports/thresholds.json kalau ada.

    Angka di SPECIES_DATA hanya nilai awal tulisan tangan. Ambang yang benar-benar
    dipakai pipeline adalah hasil kalibrasi di berkas itu, jadi seed memakai file
    tersebut supaya halaman Spesies tidak menampilkan angka yang berbeda.
    """
    try:
        from ml.ambang import muat_ambang
        return muat_ambang(ML_DIR / "reports" / "thresholds.json")
    except Exception:
        return {}


def _baca_status_konservasi() -> dict[str, tuple[str, str]]:
    """Baca ml/data/status_konservasi.csv menjadi {sci: (iucn, permen_p106)}.

    Berkas itu sumber kebenaran status konservasi, berisi rujukan per baris.
    Kalau berkas tidak ada, kembali kosong supaya seed tetap jalan.
    """
    import csv

    for basis in (ML_DIR, ROOT / "ml"):
        jalur = basis / "data" / "status_konservasi.csv"
        if not jalur.is_file():
            continue
        hasil: dict[str, tuple[str, str]] = {}
        with jalur.open(newline="", encoding="utf-8") as f:
            for baris in csv.DictReader(f):
                sci = (baris.get("scientific_name") or "").strip()
                if sci:
                    hasil[sci] = (
                        (baris.get("iucn_status") or "").strip(),
                        (baris.get("permen_p106") or "").strip(),
                    )
        return hasil
    return {}


def _gabung_spesies() -> dict[str, dict]:
    """Gabungan daftar kurasi dan daftar model, urut nama ilmiah.

    Nilai kembalian: scientific_name -> atribut kolom Species.
    """
    ambang = _baca_ambang_terkalibrasi()
    model = _daftar_model()
    status = _baca_status_konservasi()
    gabungan: dict[str, dict] = {}

    for sci, name_id, name_en, iucn, ebird, threshold in SPECIES_DATA:
        gabungan[sci] = {
            "scientific_name": sci,
            "common_name_id": name_id,
            "common_name_en": name_en,
            "iucn_status": iucn,
            "ebird_code": ebird,
            "default_threshold": ambang.get(sci, threshold),
            "model_supported": bool(model.get(sci)),
        }

    # Spesies yang hanya ada di daftar model. Nama Indonesia dan Inggris diambil
    # dari berkas model; status IUCN dan kode eBird dibiarkan kosong, bukan dikira.
    for sci, baris in model.items():
        if sci in gabungan:
            continue
        gabungan[sci] = {
            "scientific_name": sci,
            "common_name_id": baris.get("common_name_id"),
            "common_name_en": baris.get("common_name"),
            "iucn_status": None,
            "ebird_code": None,
            "default_threshold": ambang.get(sci, 0.5),
            "model_supported": True,
        }

    # Prioritas konservasi dari status resmi (CSV). Sumber prioritas dicatat
    # supaya admin tahu dari mana tanda itu berasal.
    for sci, atribut in gabungan.items():
        iucn_csv, permen = status.get(sci, ("", ""))
        if iucn_csv:
            atribut["iucn_status"] = iucn_csv
        atribut["prioritas"] = iucn_csv in ("CR", "EN", "VU") or permen == "dilindungi"
        if iucn_csv in ("CR", "EN", "VU"):
            atribut["sumber_prioritas"] = "iucn"
        elif permen == "dilindungi":
            atribut["sumber_prioritas"] = "permen_p106"
        else:
            atribut["sumber_prioritas"] = None

    return dict(sorted(gabungan.items()))


async def seed() -> None:
    tambah = perbarui = dihapus = dilewati = 0
    jumlah_model = 0

    import secrets

    # Sandi admin: dari env di production, acak di dev.
    sandi_admin = os.getenv("SEED_ADMIN_PASSWORD")
    if not sandi_admin:
        sandi_admin = secrets.token_urlsafe(16)
        if os.getenv("ENVIRONMENT") == "production":
            raise RuntimeError(
                "SEED_ADMIN_PASSWORD wajib diisi di production"
            )
        print(f"SEED_ADMIN_PASSWORD (dev, simpan untuk login): {sandi_admin}")

    async with async_session_factory() as session:
        # 1. Akun dasar, dicocokkan lewat email.
        akun = [
            ("admin@gemahutan.id", sandi_admin, UserRole.admin, "Admin"),
            ("peneliti@gemahutan.id", os.getenv("SEED_RESEARCHER_PASSWORD", sandi_admin), UserRole.researcher, "Peneliti"),
        ]
        pemilik = None
        for email, sandi, peran, nama in akun:
            hasil = await session.execute(select(User).where(User.email == email))
            user = hasil.scalar()
            if user is None:
                user = User(
                    email=email, password_hash=argon2.hash(sandi), role=peran, name=nama
                )
                session.add(user)
                await session.flush()
            if user.role != peran:
                user.role = peran
            # Akun lama dari seed sebelum 21 September bisa belum punya nama, dan
            # halaman Pengguna menampilkannya apa adanya.
            if not user.name:
                user.name = nama
            if email.startswith("admin@"):
                pemilik = user
        if pemilik is None:
            pemilik = (
                await session.execute(select(User).where(User.email == "admin@gemahutan.id"))
            ).scalar()
        await session.flush()

        # 2. Spesies, dicocokkan lewat scientific_name.
        daftar = _gabung_spesies()
        jumlah_model = sum(1 for v in daftar.values() if v["model_supported"])
        baris_lama = (await session.execute(select(Species))).scalars().all()
        indeks = {sp.scientific_name: sp for sp in baris_lama}

        for sci, atribut in daftar.items():
            ada = indeks.get(sci)
            if ada is None:
                session.add(Species(**atribut))
                tambah += 1
                continue
            berubah = False
            for kolom, nilai in atribut.items():
                if getattr(ada, kolom) != nilai:
                    setattr(ada, kolom, nilai)
                    berubah = True
            if berubah:
                perbarui += 1
        await session.flush()

        # 3. Spesies asing yang tidak dipakai deteksi mana pun dibuang.
        dipakai = set(
            (await session.execute(select(Detection.species_id).distinct())).scalars().all()
        )
        for sp in baris_lama:
            if sp.scientific_name in daftar:
                continue
            if sp.id in dipakai:
                dilewati += 1
                continue
            await session.delete(sp)
            dihapus += 1

        # 4. Lokasi sistem untuk halaman depan "Coba contoh". Dibuat di semua
        #    lingkungan termasuk produksi, tanpa koordinat sungguhan. Ini satu-
        #    satunya lokasi yang boleh dilihat akun tamu, dan tidak terlihat
        #    oleh peran petugas.
        tamu_site = (
            await session.execute(select(Site).where(Site.khusus_tamu.is_(True)))
        ).scalars().first()
        if tamu_site is None:
            session.add(
                Site(
                    name="Uji coba publik",
                    geom=None,
                    habitat_type=None,
                    owner_id=pemilik.id,
                    khusus_tamu=True,
                )
            )
            await session.flush()

        # 5. Lokasi dan satu perangkat ponsel per lokasi. Hanya di luar produksi:
        #    server produksi bersih, lokasi dan perangkat dibuat admin dari aplikasi.
        if os.getenv("ENVIRONMENT") != "production":
            lokasi_lama = (await session.execute(select(Site))).scalars().all()
            indeks_lokasi = {s.name: s for s in lokasi_lama}
            for nama, lat, lon, habitat in SITES_DATA:
                site = indeks_lokasi.get(nama)
                if site is None:
                    site = Site(
                        name=nama,
                        geom=f"SRID=4326;POINT({lon} {lat})",
                        habitat_type=habitat,
                        owner_id=pemilik.id,
                    )
                    session.add(site)
                    await session.flush()
                    indeks_lokasi[nama] = site

                nama_perangkat = f"Phone - {nama.split()[-1]}"
                hasil = await session.execute(
                    select(Device).where(Device.site_id == site.id, Device.name == nama_perangkat)
                )
                if hasil.scalar() is None:
                    session.add(
                        Device(name=nama_perangkat, type=DeviceType.phone, site_id=site.id)
                    )

        await session.commit()

    print(
        "Seed selesai. Spesies: "
        f"{tambah} ditambah, {perbarui} diperbarui, {dihapus} dihapus, "
        f"{dilewati} disimpan karena masih dipakai deteksi. "
        f"{jumlah_model} spesies ditandai model_supported."
    )


if __name__ == "__main__":
    asyncio.run(seed())
