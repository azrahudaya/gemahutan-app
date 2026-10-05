"""Estimasi arah datang suara dari rekaman banyak kanal.

Satu mikrofon tidak bisa menentukan arah sumber. Arah baru bisa diukur kalau
ada dua kanal atau lebih yang tersinkron, karena suara yang sama tiba di tiap
mikrofon pada waktu yang sedikit berbeda. Selisih waktu tiba itu diubah menjadi
sudut memakai geometri mikrofon yang diketahui.

Modul ini sengaja tidak menulis berkas dan tidak menyentuh jaringan, jadi bisa
dipanggil worker langsung. Semua fungsi yang bisa gagal karena masukan tidak
lengkap mengembalikan None, bukan melempar galat.
"""

from __future__ import annotations

from dataclasses import dataclass, field

import numpy as np

KECEPATAN_SUARA_M_S = 343.0
# Nama dan versi engine dipakai worker untuk mengisi kolom localization_engine
# dan blok localization di heartbeat. Angkanya ikut naik kalau metode berubah.
ENGINE_NAME = "gcc-phat"
ENGINE_VERSION = "1.1"
# Kanal sunyi tidak membawa informasi waktu tiba, tapi satu kanal rusak tidak
# boleh membatalkan seluruh berkas. Ambang di bawah dibuat sangat kecil supaya
# audio pelan tetap dianggap hidup.
AMBANG_SUNYI = 1e-9
# Selisih teorema waktu tiba di bawah angka ini dianggap sama, jadi dua sudut
# dengan pola selisih identik itu tidak bisa dipisahkan oleh susunan mikrofon
# yang dipakai. Dipakai untuk memisahkan arah kembar dari keraguan pengukuran.
TOLERANSI_KEMBAR_S = 1e-9
# Kandidat sudut yang jaraknya kurang dari ini dari puncak utama tidak dihitung
# sebagai pembanding, karena berdekatan dengan puncak utama itu wajar.
SUDUT_MINIMAL_ALTERNATIF = 30.0


@dataclass
class HasilArah:
    azimuth_deg: float
    galat_rms_s: float
    keyakinan: float
    tdoa_terukur: dict[tuple[int, int], float] = field(default_factory=dict)
    arah_kembar: tuple[float, ...] = ()


@dataclass
class HasilPosisi:
    x_m: float
    y_m: float
    galat_rms_deg: float
    jumlah_perangkat: int


def gcc_phat(kanal_a: np.ndarray, kanal_b: np.ndarray, sr: int, maks_lag_s: float) -> tuple[float, float]:
    """Selisih waktu kanal_a terhadap kanal_b, positif berarti kanal_a tertinggal.

    GCC-PHAT dipakai karena penyamaan fase menajamkan puncak korelasi pada suara
    bernada seperti kicauan, dibanding korelasi silang biasa.
    """
    a = np.asarray(kanal_a, dtype=np.float64).ravel()
    b = np.asarray(kanal_b, dtype=np.float64).ravel()
    # Berkas kosong atau kanal sunyi tidak punya puncak korelasi yang berarti.
    # Nilai nol dikembalikan supaya pemanggil tidak menerima nan.
    if a.size < 2 or b.size < 2 or sr <= 0:
        return 0.0, 0.0
    if float(np.max(np.abs(a))) <= AMBANG_SUNYI or float(np.max(np.abs(b))) <= AMBANG_SUNYI:
        return 0.0, 0.0

    n = a.shape[0] + b.shape[0] - 1
    n_fft = 1 << (n - 1).bit_length()
    spek_a = np.fft.rfft(a, n_fft)
    spek_b = np.fft.rfft(b, n_fft)
    silang = spek_a * np.conj(spek_b)
    besaran = np.abs(silang)
    besaran[besaran < 1e-12] = 1e-12
    korelasi = np.fft.irfft(silang / besaran, n_fft)

    maks = int(round(maks_lag_s * sr))
    # Jendela korelasi tidak boleh lebih lebar dari hasil FFT, kalau tidak
    # potongan di kedua ujung tumpang tindih dan lag terbaca dua kali.
    maks = max(1, min(maks, n_fft - 1))
    depan = np.concatenate((korelasi[-maks:], korelasi[: maks + 1]))
    posisi = int(np.argmax(np.abs(depan))) - maks
    puncak = np.abs(depan[int(np.argmax(np.abs(depan)))])

    # Interpolasi parabola pada tiga titik puncak supaya resolusi di bawah satu sampel.
    i = posisi + maks
    if 0 < i < len(depan) - 1:
        kiri, tengah, kanan = np.abs(depan[i - 1]), np.abs(depan[i]), np.abs(depan[i + 1])
        penyebut = kiri - 2 * tengah + kanan
        if abs(penyebut) > 1e-12:
            posisi = posisi + 0.5 * (kiri - kanan) / penyebut

    rerata = float(np.mean(np.abs(depan))) or 1e-12
    return posisi / sr, puncak / rerata


def tdoa_pasangan(kanal: list[np.ndarray], sr: int, maks_lag_s: float) -> dict[tuple[int, int], float]:
    hasil: dict[tuple[int, int], float] = {}
    for i in range(len(kanal)):
        for j in range(i + 1, len(kanal)):
            lag, _ = gcc_phat(kanal[i], kanal[j], sr, maks_lag_s)
            hasil[(i, j)] = lag
    return hasil


def tdoa_teori(azimuth_deg: float, geometri_xy: np.ndarray) -> dict[tuple[int, int], float]:
    """Selisih waktu tiba yang seharusnya untuk satu arah, dalam detik.

    Mikrofon yang lebih dekat ke sumber menerima suara lebih dulu, jadi waktu
    tiba kanal i adalah d_i / c dengan d_i = jarak sumber ke mikrofon i. Untuk
    sumber jauh, d_i - d_j sama dengan (p_j - p_i) dot arah menuju sumber.
    """
    theta = np.radians(azimuth_deg)
    arah = np.array([np.cos(theta), np.sin(theta)])
    proyeksi = geometri_xy @ arah / KECEPATAN_SUARA_M_S
    hasil = {}
    for i in range(len(geometri_xy)):
        for j in range(i + 1, len(geometri_xy)):
            hasil[(i, j)] = float(proyeksi[j] - proyeksi[i])
    return hasil


def estimasi_arah(kanal: list[np.ndarray], sr: int, geometri_xy: list[tuple[float, float]],
                  langkah_deg: float = 0.5) -> HasilArah | None:
    """Cari sudut yang paling cocok dengan selisih waktu yang terukur.

    Kembalikan None kalau syarat minimal tidak terpenuhi, bukan angka tebakan:
    kurang dari dua kanal, geometri tidak cocok dengan jumlah kanal, berkas
    terlalu pendek untuk memuat selisih waktu terjauh, atau kanal yang hidup
    kurang dari dua. Kanal sunyi dibuang satu per satu supaya satu mikrofon
    rusak tidak membatalkan seluruh rekaman.
    """
    if sr <= 0 or langkah_deg <= 0:
        return None

    data = [np.asarray(k, dtype=np.float64).ravel() for k in kanal]
    geo = np.asarray(geometri_xy, dtype=np.float64)
    if geo.ndim != 2 or geo.shape[1] != 2 or geo.shape[0] != len(data) or len(data) < 2:
        return None

    hidup = [
        i for i, k in enumerate(data)
        if k.size >= 2 and float(np.max(np.abs(k))) > AMBANG_SUNYI
    ]
    if len(hidup) < 2:
        return None

    # Geometri mengikuti kanal yang hidup, sehingga indeks pasangan tetap cocok.
    kanal_hidup = [data[i] for i in hidup]
    geo = geo[hidup]

    maks_lag_s = float(np.max(np.linalg.norm(geo[:, None, :] - geo[None, :, :], axis=-1)) / KECEPATAN_SUARA_M_S)
    # Berkas yang lebih pendek dari lebar jendela korelasi tidak bisa dipakai
    # mengukur lag: puncaknya jatuh di tepi dan hasilnya acak.
    sampel_minimal = int(round(maks_lag_s * sr)) + 2
    if min(k.size for k in kanal_hidup) < sampel_minimal:
        return None

    terukur = tdoa_pasangan(kanal_hidup, sr, maks_lag_s + 1.0 / sr)
    pasangan = list(terukur.keys())
    if not pasangan:
        return None

    sudut = np.arange(0.0, 360.0, langkah_deg)
    galat = np.empty(sudut.shape[0])
    teori_semua = np.empty((sudut.shape[0], len(pasangan)))
    terukur_vektor = np.array([terukur[p] for p in pasangan])
    for k, az in enumerate(sudut):
        teori = tdoa_teori(float(az), geo)
        vektor = np.array([teori[p] for p in pasangan])
        teori_semua[k] = vektor
        beda = terukur_vektor - vektor
        galat[k] = float(np.sqrt(np.mean(beda ** 2)))

    terbaik = int(np.argmin(galat))
    rms_terbaik = float(galat[terbaik])
    jarak_sudut = np.abs((sudut - sudut[terbaik] + 180) % 360 - 180)

    # Susunan mikrofon segaris memberi selisih waktu yang sama untuk sudut
    # cerminnya, jadi sudut cermin bukan tanda pengukuran yang ragu melainkan
    # batas susunan mikrofonya. Sudut seperti itu dipisahkan sebagai arah kembar
    # supaya keyakinan tidak selalu jatuh ke nol pada array garis lurus.
    selisih_teori = np.max(np.abs(teori_semua - teori_semua[terbaik]), axis=1)
    kembar = selisih_teori <= TOLERANSI_KEMBAR_S
    arah_kembar = tuple(float(a) for a in sudut[kembar & (jarak_sudut >= SUDUT_MINIMAL_ALTERNATIF)])

    luar = galat[(jarak_sudut >= SUDUT_MINIMAL_ALTERNATIF) & ~kembar]
    rms_alternatif = float(np.min(luar)) if luar.size else np.inf
    keyakinan = float(np.clip(1.0 - rms_terbaik / (rms_alternatif + 1e-12), 0.0, 1.0))

    return HasilArah(
        azimuth_deg=float(sudut[terbaik]),
        galat_rms_s=rms_terbaik,
        keyakinan=keyakinan,
        tdoa_terukur=terukur,
        arah_kembar=arah_kembar,
    )


def triangulasi(arah_per_perangkat: list[tuple[float, float, float]],
                kotak_m: float = 200.0, langkah_m: float = 2.0) -> HasilPosisi:
    """Potong beberapa arah dari perangkat berbeda menjadi satu titik.

    Tiap entri berisi posisi x, posisi y, dan azimuth derajat. Satu perangkat
    tidak cukup, dan dua perangkat hanya memberi satu titik potong tanpa sisa
    yang bisa dipakai menilai mutu.
    """
    if len(arah_per_perangkat) < 2:
        raise ValueError("butuh minimal dua perangkat untuk triangulasi")

    xs = np.arange(-kotak_m, kotak_m + langkah_m, langkah_m)
    ys = np.arange(-kotak_m, kotak_m + langkah_m, langkah_m)
    grid_x, grid_y = np.meshgrid(xs, ys)
    total = np.zeros(grid_x.shape)

    for x0, y0, az in arah_per_perangkat:
        theta = np.radians(az)
        arah = np.array([np.cos(theta), np.sin(theta)])
        vektor = np.stack([grid_x - x0, grid_y - y0], axis=-1)
        panjang = np.linalg.norm(vektor, axis=-1) + 1e-9
        cos_sudut = np.clip((vektor @ arah) / panjang, -1.0, 1.0)
        total += np.degrees(np.arccos(cos_sudut)) ** 2

    idx = np.unravel_index(int(np.argmin(total)), total.shape)
    return HasilPosisi(
        x_m=float(grid_x[idx]),
        y_m=float(grid_y[idx]),
        galat_rms_deg=float(np.sqrt(total[idx] / len(arah_per_perangkat))),
        jumlah_perangkat=len(arah_per_perangkat),
    )


def jarak_dari_selisih_level(level_ukur_db: float, level_referensi_db: float,
                             jarak_referensi_m: float) -> float | None:
    """Perkiraan jarak dari penyusutan amplitudo, hanya sah setelah dikalibrasi.

    Level referensi adalah level suara spesies pada jarak yang sudah diukur.
    Ketidakpastian level sumber 6 dB sudah menggeser hasil dua kali lipat, jadi
    angka ini dipakai sebagai jangkauan kasar, bukan posisi. Acuan yang tidak
    masuk akal dikembalikan sebagai None supaya pemanggil tidak menampilkan
    angka jarak yang salah.
    """
    acuan = (level_ukur_db, level_referensi_db, jarak_referensi_m)
    if any(v is None or not np.isfinite(v) for v in acuan) or jarak_referensi_m <= 0:
        return None
    return float(jarak_referensi_m * 10 ** ((level_referensi_db - level_ukur_db) / 20.0))


def bangun_sintetis(azimuth_deg: float, jarak_m: float, geometri_xy: list[tuple[float, float]],
                    sr: int = 16000, durasi_s: float = 1.0, snr_db: float = 20.0,
                    frekuensi_hz: float = 2000.0, benih: int = 0) -> list[np.ndarray]:
    """Rekaman buatan dengan arah dan jarak yang diketahui, untuk menguji modul ini."""
    rng = np.random.default_rng(benih)
    geo = np.asarray(geometri_xy, dtype=np.float64)
    theta = np.radians(azimuth_deg)
    sumber = np.array([np.cos(theta), np.sin(theta)]) * jarak_m

    waktu = np.arange(int(sr * durasi_s)) / sr
    # Sapuan frekuensi, bukan nada tunggal, karena nada tunggal membuat korelasi
    # silang punya banyak puncak pada selisih waktu kelipatan satu periode.
    selubung = np.exp(-((waktu - durasi_s / 2) ** 2) / (2 * (durasi_s / 8) ** 2))
    fase = 2 * np.pi * (frekuensi_hz * waktu + 1500.0 * waktu ** 2 / max(durasi_s, 1e-6))
    bersih = np.sin(fase) * selubung

    kanal = []
    for pos in geo:
        jarak_kanal = float(np.linalg.norm(sumber - pos))
        tunda = jarak_kanal / KECEPATAN_SUARA_M_S
        sinyal = np.zeros_like(waktu)
        geser = int(round(tunda * sr))
        if geser < sinyal.shape[0]:
            sinyal[geser:] = bersih[: sinyal.shape[0] - geser] * (jarak_m / max(jarak_kanal, 1e-6))
        daya = float(np.mean(sinyal ** 2)) or 1e-12
        derau = rng.normal(0.0, np.sqrt(daya / (10 ** (snr_db / 10))), sinyal.shape)
        kanal.append(sinyal + derau)
    return kanal
