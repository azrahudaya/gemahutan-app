"""Test tahap job, jalur audio multikanal, dan lokalisasi di worker.

Dijalankan di dalam image worker: `make test-worker`. Yang diuji di sini adalah
bagian yang menentukan hasil di UI, yaitu angka progres yang ditulis tiap tahap
dan pengisian arah deteksi dari audio multikanal.
"""
import numpy as np
import pytest


@pytest.fixture(autouse=True)
def bersihkan_cache_kolom():
    """Cache kolom skema di modul worker harus kosong di tiap test."""
    import worker

    worker._KOLOM.clear()
    worker._PERINGATAN_SEKALI.clear()
    yield
    worker._KOLOM.clear()


@pytest.fixture(scope="module")
def audio_empat_kanal(tmp_path_factory):
    """Wav empat kanal dari sinyal buatan, arah datangnya diketahui."""
    import soundfile as sf

    from ml.localization import bangun_sintetis

    sr = 16000
    geometri = [(0.0, 0.0), (0.5, 0.0), (1.0, 0.0), (1.5, 0.0)]
    kanal = bangun_sintetis(60.0, 25.0, geometri, sr=sr, durasi_s=1.0, snr_db=20.0, benih=3)
    folder = tmp_path_factory.mktemp("multikanal")
    berkas = folder / "empat_kanal.wav"
    sf.write(str(berkas), np.stack(kanal, axis=1), sr, subtype="PCM_16")

    stereo = folder / "stereo.wav"
    sf.write(str(stereo), np.stack(kanal[:2], axis=1), sr, subtype="PCM_16")

    mono = folder / "mono.wav"
    sf.write(str(mono), kanal[0], sr, subtype="PCM_16")
    return berkas, stereo, mono


class HasilPalsu:
    def __init__(self, baris):
        self._baris = baris

    def all(self):
        return self._baris

    def fetchone(self):
        return self._baris[0] if self._baris else None

    def scalar(self):
        return self._baris[0][0] if self._baris else None


class SesiPalsu:
    """Sesi sqlalchemy tiruan, cukup untuk menguji pernyataan yang ditulis worker."""

    def __init__(self, kolom: dict[str, list[str]]):
        self.kolom = kolom
        self.pernyataan: list[tuple[str, dict]] = []
        self.commit_dipanggil = 0

    def execute(self, pernyataan, parameter=None):
        teks = str(pernyataan)
        if "information_schema.columns" in teks:
            tabel = (parameter or {}).get("tabel")
            return HasilPalsu([(nama,) for nama in self.kolom.get(tabel, [])])
        self.pernyataan.append((teks, parameter or {}))
        return HasilPalsu([])

    def commit(self):
        self.commit_dipanggil += 1


def test_tahap_dan_progres_sesuai_kontrak():
    """Angka progres dipatok kontrak, bukan dihitung ulang tiap rekaman."""
    import worker

    assert worker.PROGRES == {
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
    assert worker.TAHAP == (
        "antre", "unduh", "dekode", "birdnet", "klasifikasi",
        "lokalisasi", "indeks", "spektrogram", "selesai", "gagal",
    )


def test_progres_ditulis_ke_jobs():
    import worker

    sesi = SesiPalsu({"jobs": ["id", "recording_id", "status", "progress", "stage"]})
    worker.tulis_progres(sesi, 12, "lokalisasi", 80)

    assert len(sesi.pernyataan) == 1
    teks, parameter = sesi.pernyataan[0]
    assert "UPDATE jobs SET" in teks
    assert "progress = :progress" in teks
    assert "stage = :tahap" in teks
    assert parameter == {"rid": 12, "tahap": "lokalisasi", "progress": 80}
    assert sesi.commit_dipanggil == 1


def test_progres_dilewati_kalau_kolom_belum_ada():
    """Migrasi yang belum jalan tidak boleh menggagalkan rekaman."""
    import worker

    sesi = SesiPalsu({"jobs": ["id", "recording_id", "status"]})
    worker.tulis_progres(sesi, 12, "unduh", 10)

    assert sesi.pernyataan == []
    assert sesi.commit_dipanggil == 0


def test_tahap_asing_ditolak():
    import worker

    sesi = SesiPalsu({"jobs": ["id", "recording_id", "progress", "stage"]})
    with pytest.raises(ValueError):
        worker.tulis_progres(sesi, 12, "menghitung", 50)


def test_berkas_empat_kanal_dipisah_mono_dan_multikanal(audio_empat_kanal):
    """Kanal tidak boleh dibuang: model dapat mono, lokalisasi dapat empat kanal."""
    import soundfile as sf
    import worker

    sumber, _, _ = audio_empat_kanal
    jalur = worker.siapkan_audio_jalur(sumber)

    assert jalur.kanal == 4
    assert jalur.multikanal == sumber
    assert sf.info(str(jalur.mono)).channels == 1
    assert sf.info(str(jalur.multikanal)).channels == 4
    assert jalur.mono != sumber

    jalur.bersihkan()
    assert not jalur.mono.exists()
    assert sumber.exists()


def test_stereo_wav_juga_dipaksa_mono_untuk_model(audio_empat_kanal):
    import soundfile as sf
    import worker

    _, stereo, _ = audio_empat_kanal
    jalur = worker.siapkan_audio_jalur(stereo)

    assert jalur.kanal == 2
    assert jalur.multikanal == stereo
    assert sf.info(str(jalur.mono)).channels == 1
    jalur.bersihkan()


def test_mono_tidak_menyiapkan_jalur_multikanal(audio_empat_kanal):
    import worker

    _, _, mono = audio_empat_kanal
    jalur = worker.siapkan_audio_jalur(mono)

    assert jalur.kanal == 1
    assert jalur.multikanal is None
    assert jalur.mono == mono


def test_m4a_stereo_dikonversi_dan_kanalnya_dipertahankan(audio_empat_kanal, tmp_path):
    """Format ponsel dikonversi, tapi jumlah kanalnya tidak dikurangi."""
    import subprocess

    import soundfile as sf
    import worker

    _, stereo, _ = audio_empat_kanal
    m4a = tmp_path / "stereo.m4a"
    subprocess.run(
        ["ffmpeg", "-y", "-hide_banner", "-loglevel", "error", "-i", str(stereo),
         "-c:a", "aac", str(m4a)],
        check=True,
    )

    jalur = worker.siapkan_audio_jalur(m4a)
    assert jalur.kanal == 2
    assert jalur.multikanal is not None and jalur.multikanal != m4a
    assert sf.info(str(jalur.multikanal)).channels == 2
    assert sf.info(str(jalur.mono)).channels == 1
    jalur.bersihkan()


def test_lokalisasi_jendela_menemukan_azimuth(audio_empat_kanal):
    """Arah yang diketahui harus terbaca dalam toleransi beberapa derajat."""
    import worker

    sumber, _, _ = audio_empat_kanal
    data, sr = worker.muat_multikanal(sumber)
    assert data.shape[0] == 4

    geometri = worker.geometri_linier(4, 0.5)
    hasil = worker.lokalisasi_jendela(data, sr, geometri, 0.1, 0.9)

    assert hasil["localization_engine"] == "gcc-phat"
    assert hasil["azimuth_deg"] is not None
    selisih = abs((hasil["azimuth_deg"] - 60.0 + 180) % 360 - 180)
    assert selisih < 5.0
    assert 0.0 <= hasil["azimuth_confidence"] <= 1.0
    # Tanpa acuan terkalibrasi, jangkauan tidak diisi.
    assert hasil["range_m"] is None


def test_jangkauan_hanya_diisi_kalau_perangkat_terkalibrasi(audio_empat_kanal):
    import worker

    sumber, _, _ = audio_empat_kanal
    data, sr = worker.muat_multikanal(sumber)
    geometri = worker.geometri_linier(4, 0.5)

    hasil = worker.lokalisasi_jendela(data, sr, geometri, 0.1, 0.9, acuan_jarak=(10.0, -20.0))

    assert hasil["range_m"] is not None
    assert hasil["range_m"] > 0


def test_jendela_satu_kanal_tidak_menghasilkan_arah(audio_empat_kanal):
    """Kanal kurang dari dua: semua kolom lokalisasi tetap kosong."""
    import worker

    sumber, _, _ = audio_empat_kanal
    data, sr = worker.muat_multikanal(sumber)

    hasil = worker.lokalisasi_jendela(data[:1], sr, worker.geometri_linier(1, 0.5), 0.1, 0.9)

    assert hasil == {
        "azimuth_deg": None,
        "azimuth_confidence": None,
        "azimuth_kembar_deg": None,
        "range_m": None,
        "localization_engine": None,
    }


def test_jendela_kanal_sunyi_tidak_melempar_galat():
    """Kanal rusak yang sunyi harus dilewati, bukan menggagalkan rekaman."""
    import worker

    sr = 16000
    panjang = sr
    sunyi = np.zeros(panjang)
    hidup = np.sin(2 * np.pi * 1000 * np.arange(panjang) / sr)
    data = np.stack([sunyi, sunyi, hidup, hidup])

    hasil = worker.lokalisasi_jendela(data, sr, worker.geometri_linier(4, 0.5), 0.0, 1.0)

    assert "azimuth_deg" in hasil


def test_terapkan_lokalisasi_mengisi_kolom_deteksi(audio_empat_kanal):
    import worker

    sumber, _, _ = audio_empat_kanal
    sesi = SesiPalsu({
        "detections": [
            "id", "recording_id", "confidence", "start_s", "end_s",
            "azimuth_deg", "azimuth_confidence", "azimuth_kembar_deg",
            "range_m", "localization_engine",
        ],
    })
    id_deteksi = [(7, {"start_s": 0.1, "end_s": 0.9})]

    jumlah = worker.terapkan_lokalisasi(sesi, id_deteksi, sumber, 4, 0.5, None)

    assert jumlah == 1
    assert len(sesi.pernyataan) == 1
    teks, parameter = sesi.pernyataan[0]
    assert "UPDATE detections" in teks
    assert parameter["id"] == 7
    assert parameter["eng"] == "gcc-phat"
    assert abs((parameter["az"] - 60.0 + 180) % 360 - 180) < 5.0
    # Array segaris selalu punya sudut cermin yang sama sah.
    assert abs((parameter["kembar"] - 300.0 + 180) % 360 - 180) < 5.0
    assert parameter["jarak"] is None


def test_terapkan_lokalisasi_dilewati_tanpa_spacing(audio_empat_kanal):
    """Perangkat tanpa mic_spacing_m berarti arah tidak boleh ditebak."""
    import worker

    sumber, _, _ = audio_empat_kanal
    sesi = SesiPalsu({"detections": ["id", "azimuth_deg"]})
    id_deteksi = [(7, {"start_s": 0.1, "end_s": 0.9})]

    assert worker.terapkan_lokalisasi(sesi, id_deteksi, sumber, 4, None, None) == 0
    assert sesi.pernyataan == []


def test_terapkan_lokalisasi_dilewati_kalau_kolom_belum_ada(audio_empat_kanal):
    import worker

    sumber, _, _ = audio_empat_kanal
    sesi = SesiPalsu({"detections": ["id", "recording_id", "confidence"]})
    id_deteksi = [(7, {"start_s": 0.1, "end_s": 0.9})]

    assert worker.terapkan_lokalisasi(sesi, id_deteksi, sumber, 4, 0.5, None) == 0
    assert sesi.pernyataan == []


def test_arah_kembar_dilaporkan_untuk_susunan_segaris(audio_empat_kanal):
    """Susunan mikrofon segaris tidak memisahkan 60 derajat dari 300 derajat.

    Tanpa pemisahan ini, sudut cermin masuk hitungan pembanding dan keyakinan
    arah jatuh mendekati nol walaupun pengukurannya tepat.
    """
    import worker

    sumber, _, _ = audio_empat_kanal
    data, sr = worker.muat_multikanal(sumber)
    geometri = worker.geometri_linier(4, 0.5)

    hasil = worker.lokalisasi_jendela(data, sr, geometri, 0.0, 1.0, None)

    assert hasil["azimuth_deg"] is not None
    assert abs((hasil["azimuth_deg"] - 60.0 + 180) % 360 - 180) < 5.0
    assert hasil["azimuth_kembar_deg"] is not None
    assert abs((hasil["azimuth_kembar_deg"] - 300.0 + 180) % 360 - 180) < 5.0
    assert hasil["azimuth_confidence"] > 0.3
    assert hasil["range_m"] is None


def test_blok_lokalisasi_heartbeat_sesuai_kontrak():
    """Bentuk blok ini dikunci kontrak, endpoint /model/info membacanya."""
    import worker

    assert worker.info_lokalisasi() == {
        "terpasang": True,
        "kanal_minimal": 2,
        "engine": "gcc-phat",
        "versi": "1.1",
    }
