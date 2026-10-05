"""Bangun semua diagram proposal: python3 docs/assets/diagram_src/buat_diagram.py

Keluaran di docs/assets/diagrams/: <nama>.drawio (bisa diedit di draw.io) dan <nama>.png.
Isi diagram mengikuti kode di repo per 29 September 2026 (commit 385147c).
"""
from pathlib import Path

from diagram_lib import (
    ABU,
    ABU_TEPI,
    BIRU,
    BIRU_MUDA,
    GARIS,
    MINT,
    MINT_TEPI,
    PUTIH,
    TEKS2,
    TINTA,
    Diagram,
    Edge,
    Grup,
    Node,
    Teks,
)

OUT = Path(__file__).resolve().parent.parent / "diagrams"


def biru(**kw):
    return dict(isi=BIRU, tepi=BIRU, warna_teks=PUTIH, **kw)


def biru_muda(**kw):
    return dict(isi=BIRU_MUDA, tepi=BIRU, **kw)


def mint(**kw):
    return dict(isi=MINT, tepi=MINT_TEPI, **kw)


# ---------------------------------------------------------------- arsitektur
def arsitektur():
    d = Diagram("arsitektur", 800, 550)
    d.node += [
        Node("user", 20, 20, 160, 62, "Pengguna\nranger, peneliti, admin\n(desktop atau ponsel)"),
        Node("web", 240, 20, 215, 62, "Web Next.js 15 (PWA)\nrekam, unggah, verifikasi,\nlaporan, simulasi lokasi", **biru_muda()),
        Node("api", 525, 20, 255, 62, "API FastAPI\nJWT + 3 peran, undangan akun,\nsamarkan lokasi spesies prioritas", **biru()),
        Node("pg", 20, 160, 240, 62, "PostgreSQL 16 + PostGIS\nrekaman, deteksi, verifikasi,\nlokasi, jejak audit"),
        Node("redis", 280, 160, 240, 62, "Redis 7\nantrean job (ARQ), pencabutan\ntoken, pembatas laju"),
        Node("minio", 540, 160, 240, 62, "MinIO (S3)\nberkas audio asli\ndan spektrogram"),
        Node("bn", 36, 312, 200, 50, "Track A: BirdNET 2.4\nzero-shot, 6.522 spesies"),
        Node("tb", 36, 372, 200, 62, "Track B: embedding 1024\n+ regresi logistik,\n25 spesies Indonesia", **mint()),
        Node("gab", 270, 336, 180, 76, "Gabung hasil\nambang per spesies\n+ penyaring deteksi\nlemah"),
        Node("lok", 484, 372, 281, 62, "Lokalisasi GCC-PHAT + triangulasi\nrekaman ≥2 kanal, juga dipakai\nsimulasi alat virtual"),
        Node("idx", 484, 312, 281, 50, "Indeks soundscape + spektrogram\nACI, NDSI, ADI, BI dari audio yang sama"),
        Node("and", 36, 492, 330, 40, "Alat perekam berjam GPS (Tahap 2-3)", putus=True, isi=PUTIH, judul_tebal=False, ukuran=12.5),
        Node("edge", 380, 492, 385, 40, "Peringatan email spesies prioritas (SMTP)", isi=PUTIH, judul_tebal=False, ukuran=12.5),
    ]
    d.grup += [
        Grup("gw", 20, 278, 760, 170, "Worker ARQ (Python, CPU): memproses satu rekaman per job"),
        Grup("gr", 20, 462, 760, 80, "Di luar inti: alat lapangan (rencana, garis putus) dan layanan email", putus=True),
    ]
    d.edge += [
        Edge((180, 51), (240, 51), label="HTTPS", label_pos=(210, 38)),
        Edge((455, 51), (525, 51), label="REST, SSE", label_pos=(490, 38)),
        Edge((545, 82), (140, 160), via=[(545, 118), (140, 118)], label="baca/tulis data", label_pos=(330, 118)),
        Edge((600, 82), (400, 160), via=[(600, 138), (400, 138)], label="masukkan job", label_pos=(480, 138)),
        Edge((690, 82), (690, 160), label="simpan audio", label_pos=(690, 118)),
        Edge((400, 222), (400, 278), label="ambil job", label_pos=(400, 250)),
        Edge((690, 278), (690, 222), label="unduh audio,\nsimpan spektrogram", label_pos=(690, 250)),
        Edge((140, 278), (140, 222), label="simpan deteksi\ndan indeks", label_pos=(140, 250)),
        Edge((236, 337), (270, 360), via=[(253, 337), (253, 360)]),
        Edge((236, 403), (270, 390), via=[(253, 403), (253, 390)]),
        Edge((450, 395), (484, 395)),
    ]
    return d


# ------------------------------------------------------------ alur pemrosesan
def alur():
    d = Diagram("alur_pemrosesan", 800, 600)
    d.node += [
        Node("a", 20, 20, 235, 58, "1. Unggah atau rekam\nweb: 1-20 berkas, maks. 200 MB"),
        Node("b", 283, 20, 235, 58, "2. Validasi isi audio\nffprobe: harus berisi audio"),
        Node("c", 545, 20, 235, 58, "3. Simpan ke MinIO\n+ buat job di antrean Redis"),
        Node("d", 230, 110, 340, 58, "4. Worker: unduh dan dekode\nmono 48 kHz, jendela 3 detik", **biru()),
        Node("e", 40, 206, 320, 70, "5a. Track A: BirdNET 2.4 (zero-shot)\n6.522 spesies global, dengan filter\nwilayah dari koordinat lokasi"),
        Node("f", 440, 206, 320, 70, "5b. Track B: embedding BirdNET 1024\n→ regresi logistik 25 spesies\n+ kalibrasi suhu dan bias", **mint()),
        Node("g", 200, 312, 400, 58, "6. Gabung hasil, ambang per spesies, penyaring:\nbuang < 1 dtk; keyakinan < 0,5 harus muncul ≥2 kali"),
        Node("h", 20, 410, 235, 52, "7. Indeks soundscape\nACI, NDSI, ADI, BI (scikit-maad)"),
        Node("i", 283, 410, 235, 52, "8. Spektrogram\n(disimpan di MinIO)"),
        Node("j", 545, 410, 235, 52, "9. Lokalisasi arah\nbila rekaman ≥2 kanal"),
        Node("k", 20, 510, 235, 58, "10. PostgreSQL + PostGIS\ndeteksi, indeks, status job"),
        Node("l", 283, 510, 235, 58, "11. Dashboard, peta,\ndetail rekaman, ekspor", **biru_muda()),
        Node("m", 545, 510, 235, 58, "12. Verifikasi ahli\nbenar / salah / ragu", **biru_muda()),
    ]
    d.edge += [
        Edge((255, 49), (283, 49)),
        Edge((518, 49), (545, 49)),
        Edge((662, 78), (570, 139), via=[(662, 139)]),
        Edge((330, 168), (200, 206), via=[(330, 187), (200, 187)]),
        Edge((470, 168), (600, 206), via=[(470, 187), (600, 187)]),
        Edge((200, 276), (330, 312), via=[(200, 294), (330, 294)]),
        Edge((600, 276), (470, 312), via=[(600, 294), (470, 294)]),
        Edge((400, 370), (137, 410), via=[(400, 390), (137, 390)]),
        Edge((400, 370), (400, 410)),
        Edge((400, 390), (662, 410), via=[(662, 390)]),
        Edge((137, 462), (137, 510)),
        Edge((400, 462), (400, 486), via=[], panah=False),
        Edge((662, 462), (662, 486), panah=False),
        Edge((662, 486), (137, 486), panah=False),
        Edge((255, 539), (283, 539)),
        Edge((518, 539), (545, 539)),
        Edge((780, 539), (760, 241), via=[(792, 539), (792, 241)], putus=True, warna=MINT_TEPI,
             label="data latih ulang\n(lewat gerbang)", label_pos=(733, 487)),
    ]
    return d


# ------------------------------------------------------------------ ERD
def erd():
    d = Diagram("erd", 800, 470)

    def tabel(id_, x, y, w, nama, kolom, **kw):
        h = 24 + 15.5 * len(kolom)
        d.node.append(Node(id_, x, y, w, h, nama + "\n" + "\n".join(kolom), rata="kiri", ukuran=13, **kw))
        return (x, y, w, h)

    tabel("users", 20, 20, 170, "users", ["id (PK)", "email, name", "role: admin/peneliti/ranger", "password_hash (argon2)", "token_version"])
    tabel("sites", 230, 20, 170, "sites", ["id (PK)", "name, habitat_type", "location (PostGIS)", "owner_id → users"])
    tabel("devices", 440, 20, 170, "devices", ["id (PK)", "site_id → sites", "channel_count", "mic_spacing_m"])
    tabel("species", 630, 20, 150, "species", ["id (PK)", "scientific_name", "common_name_id", "default_threshold", "model_supported"])
    tabel("rec", 230, 185, 190, "recordings", ["id (PK)", "site_id → sites", "device_id → devices", "uploaded_by → users", "storage_key, batch_id", "status, recorded_at"], **biru_muda())
    tabel("det", 470, 185, 220, "detections", ["id (PK)", "recording_id → recordings", "species_id → species", "confidence, start_s, end_s", "verified_status, verified_by", "azimuth_deg, range_m"], **biru_muda())
    tabel("job", 20, 185, 170, "jobs", ["id (PK)", "recording_id (1:1)", "status, progress, stage", "attempts, last_error"])
    tabel("idx", 20, 345, 170, "acoustic_indices", ["id (PK)", "recording_id (1:1)", "aci, ndsi, adi, bi"])
    tabel("audit", 470, 368, 180, "audit_logs", ["id (PK)", "actor_id → users", "action, entity, ip"])
    tabel("reset", 230, 368, 190, "password_reset_tokens", ["id (PK)", "user_id → users", "token_hash (SHA-256)"])
    d.tinggi = 488

    def rel(pts, lbl_a, pos_a, lbl_b, pos_b, **kw):
        d.edge.append(Edge(pts[0], pts[-1], via=list(pts[1:-1]), panah=False, **kw))
        d.teks.append(Teks(pos_a[0], pos_a[1], lbl_a, ukuran=11, tebal=True, warna=BIRU))
        d.teks.append(Teks(pos_b[0], pos_b[1], lbl_b, ukuran=11, tebal=True, warna=BIRU))

    # tepi kotak: users bawah 121.5, sites/devices bawah 106, species bawah 121.5,
    # recordings & detections 185..302, jobs 185..271, acoustic_indices 345..415.5
    rel([(190, 62), (230, 62)], "1", (194, 46), "N", (219, 46))                       # users -> sites
    rel([(400, 62), (440, 62)], "1", (404, 46), "N", (429, 46))                       # sites -> devices
    rel([(315, 106), (315, 185)], "1", (320, 108), "N", (320, 166))                   # sites -> recordings
    rel([(525, 106), (525, 150), (400, 150), (400, 185)], "1", (530, 108), "N", (405, 166))  # devices -> recordings
    rel([(705, 121.5), (705, 150), (660, 150), (660, 185)], "1", (710, 123), "N", (665, 166))  # species -> detections
    rel([(420, 245), (470, 245)], "1", (424, 229), "N", (459, 229))                   # recordings -> detections
    rel([(230, 228), (190, 228)], "1", (218, 212), "1", (194, 212))                   # recordings -> jobs
    rel([(230, 290), (210, 290), (210, 380), (190, 380)], "1", (216, 274), "1", (194, 364))  # recordings -> indices
    rel([(105, 121.5), (105, 165), (272, 165), (272, 185)], "1", (110, 123), "N", (277, 166),
        warna=ABU_TEPI, putus=True)                                                      # users -> recordings
    d.teks.append(Teks(20, 448, "Garis putus: recordings.uploaded_by → users. Relasi users → audit_logs, password_reset_tokens,\n"
                                "dan detections.verified_by ada di skema tetapi tidak digambar supaya diagram tetap terbaca.",
                       ukuran=10.5, miring=True))
    return d


# ------------------------------------------------------------------ tahapan
def tahapan():
    import datetime as dt
    d = Diagram("tahapan", 800, 420)
    tahap = [
        ("Tahap 1\nPerangkat lunak", "model 25 spesies,\naplikasi 3 peran,\nverifikasi, laporan,\nsimulasi lokasi", True),
        ("Tahap 2\nUji lapangan", "satu kawasan mitra,\nalat terpasang,\nakurasi lapangan\nresmi", False),
        ("Tahap 3\nJaringan alat", "jam tersinkron GPS,\nperkiraan area asal\nsuara dari data nyata", False),
        ("Tahap 4\nPeluang dan ancaman", "peta peluang\nkeberadaan, suara\ngergaji, tembakan", False),
        ("Tahap 5\nSkala nasional", "banyak kawasan,\nakses per kawasan,\ndata terbuka", False),
    ]
    w, gap = 146, 9
    for i, (judul, isi, aktif) in enumerate(tahap):
        x = 20 + i * (w + gap)
        kw = biru(judul_tebal=True, ukuran=12.5) if aktif else dict(isi=PUTIH, tepi=BIRU, putus=True, ukuran=12.5)
        d.node.append(Node(f"t{i}", x, 20, w, 48, judul, **kw))
        d.node.append(Node(f"i{i}", x, 74, w, 78, isi, isi=BIRU_MUDA if aktif else PUTIH, tepi=BIRU if aktif else ABU_TEPI,
                           judul_tebal=False, ukuran=11))
        if i:
            d.edge.append(Edge((x - gap, 44), (x, 44)))
    d.teks.append(Teks(20, 162, "Linimasa Tahap 1 (terisi: sudah dikerjakan menurut riwayat commit; garis putus: rencana)",
                       ukuran=11, tebal=True, warna=TEKS2))
    mulai, akhir = dt.date(2026, 9, 14), dt.date(2026, 11, 19)
    x0, x1 = 300, 770
    hari = (akhir - mulai).days

    def X(t):
        return x0 + (t - mulai).days / hari * (x1 - x0)

    for label, tgl in [("14 Sep", dt.date(2026, 9, 14)), ("1 Okt", dt.date(2026, 10, 1)),
                       ("1 Nov", dt.date(2026, 11, 1)), ("19 Nov", dt.date(2026, 11, 19))]:
        d.teks.append(Teks(X(tgl) - 8, 184, label, ukuran=10.5, tebal=True, warna=TEKS2))
        d.edge.append(Edge((X(tgl), 200), (X(tgl), 396), panah=False, warna="#E4E4E7"))
    baris = [
        ("Fondasi, fitur inti, keamanan", dt.date(2026, 9, 14), dt.date(2026, 9, 22), True),
        ("Evaluasi model, audit mutu", dt.date(2026, 9, 23), dt.date(2026, 9, 30), True),
        ("Deploy gemahutan.site, backup", dt.date(2026, 10, 1), dt.date(2026, 10, 3), True),
        ("Aplikasi 3 peran, prioritas, simulasi", dt.date(2026, 10, 3), dt.date(2026, 10, 5), True),
        ("Uji SUS dan uji black-box", dt.date(2026, 10, 5), dt.date(2026, 10, 5), True),
        ("Rekam lapangan, laporan bulanan", dt.date(2026, 10, 6), dt.date(2026, 10, 9), False),
        ("Presentasi seleksi, video, final", dt.date(2026, 10, 13), dt.date(2026, 11, 19), False),
    ]
    for i, (nama, a, b, selesai) in enumerate(baris):
        y = 204 + i * 27
        d.teks.append(Teks(20, y + 2, nama, ukuran=11.5, warna=TINTA if selesai else TEKS2))
        kw = biru(judul_tebal=False) if selesai else dict(isi=PUTIH, tepi=BIRU, putus=True, judul_tebal=False)
        d.node.append(Node(f"b{i}", X(a), y, max(X(b) - X(a), 6), 18, "", radius=3, **kw))
    return d


# ------------------------------------------------------------------ mockup
def mockup():
    d = Diagram("mockup", 800, 500)
    abu = dict(isi=ABU, tepi=ABU_TEPI, judul_tebal=False, ukuran=11.5)
    # ---- (a) ponsel: rekam dari peramban
    d.grup.append(Grup("hp", 20, 20, 230, 440, "(a) Ponsel: rekam dari peramban"))
    d.node += [
        Node("hp_judul", 34, 50, 202, 26, "Rekam dari peramban", isi=PUTIH, tepi=PUTIH, rata="kiri", ukuran=13),
        Node("hp_lok", 34, 84, 202, 30, "Lokasi perekaman            v", rata="kiri", **abu),
        Node("hp_dev", 34, 122, 202, 30, "Perangkat (opsional)        v", rata="kiri", **abu),
        Node("hp_timer", 34, 164, 202, 60, "00:00\ndurasi rekaman", isi=PUTIH, tepi=ABU_TEPI, ukuran=15),
        Node("hp_level", 34, 232, 202, 26, "level sinyal mikrofon   | | | | . . . .", rata="kiri", **abu),
        Node("hp_mulai", 34, 272, 202, 36, "Mulai rekam", **biru(judul_tebal=True, ukuran=12.5)),
        Node("hp_stop", 34, 316, 202, 36, "Berhenti dan unggah", isi=PUTIH, tepi=GARIS, ukuran=12.5),
        Node("hp_note", 34, 362, 202, 84, "Setelah unggah: status\n'antre → diproses → selesai'\ntampil otomatis (SSE),\nlalu tautan ke hasil.", isi=PUTIH, tepi=PUTIH, judul_tebal=False, ukuran=11.5),
    ]
    # ---- (b) simulasi perkiraan lokasi
    d.grup.append(Grup("pc", 280, 20, 500, 440, "(b) Simulasi perkiraan lokasi"))
    d.grup.append(Grup("peta", 294, 84, 330, 290, "peta kawasan"))
    d.node += [
        Node("pc_judul", 294, 50, 300, 26, "Simulasi lokasi · alat virtual", isi=PUTIH, tepi=PUTIH, rata="kiri", ukuran=13),
        Node("pc_stat", 650, 50, 116, 24, "Bukan data nyata", **mint(judul_tebal=True, ukuran=10.5)),
        Node("pc_a1", 318, 330, 22, 22, "1", **biru(judul_tebal=True, ukuran=10.5)),
        Node("pc_a2", 576, 318, 22, 22, "2", **biru(judul_tebal=True, ukuran=10.5)),
        Node("pc_a3", 446, 104, 22, 22, "3", **biru(judul_tebal=True, ukuran=10.5)),
        Node("pc_area", 488, 214, 46, 36, "", isi=BIRU_MUDA, tepi=BIRU, radius=18),
        Node("pc_src", 504, 225, 14, 14, "", **mint(radius=7)),
        Node("pc_f1", 634, 84, 132, 30, "Jumlah alat: 3     v", rata="kiri", **abu),
        Node("pc_f2", 634, 120, 132, 30, "Jenis: larik 4 mik   v", rata="kiri", **abu),
        Node("pc_f3", 634, 156, 132, 30, "Derau: 10 dB       v", rata="kiri", **abu),
        Node("pc_f4", 634, 192, 132, 30, "Jam sinkron   [x]", rata="kiri", **abu),
        Node("pc_run", 634, 232, 132, 34, "Hitung", **biru(judul_tebal=True, ukuran=12)),
        Node("pc_hasil", 634, 276, 132, 98, "Arah alat 1: 32°\nArah alat 2: 141°\nArah alat 3: 285°\nSelisih ke\nsumber: 1,0 m",
             isi=PUTIH, tepi=ABU_TEPI, rata="kiri", judul_tebal=False, ukuran=11),
        Node("pc_note", 294, 386, 472, 60, "Seret alat dan sumber suara di peta. Garis menunjukkan arah dari tiap\n"
             "alat; bidang hijau adalah area perkiraan. Satu alat saja hanya memberi arah.",
             isi=PUTIH, tepi=PUTIH, judul_tebal=False, ukuran=11, rata="kiri"),
    ]
    for (x0, y0) in [(329, 341), (587, 329), (457, 115)]:
        d.edge.append(Edge((x0, y0), (511, 232), panah=False, warna=BIRU))
    d.teks.append(Teks(20, 470, "Wireframe resolusi rendah; tampilan akhir memakai tema hijau aplikasi (lihat bagian tangkapan layar).",
                       ukuran=10.5, miring=True))
    return d


if __name__ == "__main__":
    for f in (arsitektur, alur, erd, tahapan, mockup):
        p = f().simpan(OUT)
        print("ok", p)
