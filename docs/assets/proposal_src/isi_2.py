"""Isi proposal bagian 2: analisis kebutuhan dan desain, implementasi."""
from data import koma


def _ik(a, b):
    return f"{koma(a)} sampai {koma(b)}"


def _sim(f):
    d = f["sim"]["per_snr"]
    return (f"{koma(d['20']['median_m'], 1)} m pada SNR 20 dB dan {koma(d['0']['median_m'], 1)} m pada SNR 0 dB, "
            f"dengan persentil 90 paling besar {koma(max(v['p90_m'] for v in d.values()), 1)} m")


def isi(f):
    cv, e, ind = f["cv"], f["e2e"], f["ind"]
    b = [
        ("h1", "6. ANALISIS KEBUTUHAN DAN DESAIN SOLUSI PERANGKAT LUNAK"),
        ("h2", "6.1 Pengguna dan Hak Akses"),
        ("p", "GemaHutan dibuat untuk petugas konservasi, bukan masyarakat umum. Akun hanya dibuat admin melalui "
              "undangan surel; tidak ada pendaftaran mandiri. Hak akses ditegakkan di API, bukan hanya disembunyikan "
              "di antarmuka (Tabel 2). Pengunjung halaman depan dapat mencoba satu unggahan dengan akun tamu "
              "terisolasi yang dihapus otomatis setelah 24 jam."),
        ("tbl", "Peran pengguna dan hak aksesnya", ["Peran", "Siapa", "Hak akses"], [
            ["Admin", "Pengelola balai taman nasional atau BKSDA",
             "Semua fitur; kelola akun, lokasi, perangkat, dan spesies prioritas; lokasi tepat spesies prioritas"],
            ["Peneliti", "Ahli burung, peneliti mitra",
             "Semua rekaman; verifikasi; ekspor; dasbor, peta, laporan; halaman Model dan Perangkat; lokasi tepat spesies prioritas"],
            ["Ranger", "Polisi hutan, petugas lapangan, relawan",
             "Rekam dan unggah; hasil rekamannya sendiri; simulasi perkiraan lokasi"],
        ], [2.2, 4.3, 9.5]),
        ("h2", "6.2 Kebutuhan Fungsional"),
        ("tbl", "Kebutuhan fungsional", ["Kode", "Kebutuhan"], [
            ["KF-01", "Masuk dan keluar; admin mengundang akun lewat surel; atur ulang sandi lewat tautan sekali pakai"],
            ["KF-02", "Admin mengelola lokasi pemantauan (koordinat), perangkat perekam (jumlah kanal, jarak mikrofon), dan spesies prioritas"],
            ["KF-03", "Mengunggah 1 sampai 20 berkas audio sekaligus, atau merekam langsung dari peramban ponsel"],
            ["KF-04", "Memproses rekaman di antrean dan menampilkan tahap serta progresnya secara langsung"],
            ["KF-05", "Mendeteksi spesies dengan dua jalur (BirdNET global dan pengklasifikasi lokal) dan ambang per spesies"],
            ["KF-06", "Menampilkan pemutar audio, spektrogram, dan daftar deteksi; indeks *soundscape* untuk admin dan peneliti"],
            ["KF-07", "Dasbor, peta kawasan, dan laporan bulanan per kawasan yang siap cetak (admin dan peneliti)"],
            ["KF-08", "Verifikasi deteksi oleh peneliti atau admin: benar, salah, atau ragu"],
            ["KF-09", "Ekspor deteksi terverifikasi (CSV atau JSON) untuk admin dan peneliti"],
            ["KF-10", "Menandai spesies prioritas (IUCN CR, EN, VU dan Permen LHK P.106/2018), menyamarkan lokasinya bagi peran lain, dan mengirim peringatan surel"],
            ["KF-11", "Simulasi perkiraan lokasi: menaruh alat virtual di peta dan melihat area perkiraan asal suara"],
            ["KF-12", "Menyimpan audio penuh 90 hari, lalu hanya potongan di sekitar deteksi; mencatat jejak audit tindakan penting"],
        ], [2.0, 14.0]),
        ("h2", "6.3 Kebutuhan Non-Fungsional"),
        ("bul", [
            "**Keamanan:** token JWT dengan pencabutan saat keluar, sandi disimpan sebagai *hash* Argon2, kontrol akses per "
            "peran dan per objek, pembatas laju, validasi isi berkas audio.",
            "**Kerahasiaan lokasi:** koordinat tepat deteksi spesies prioritas hanya dikirim API kepada admin dan "
            "peneliti; peran lain menerima koordinat yang dibulatkan.",
            f"**Kinerja:** rekaman 60 menit diproses sekitar {f['latensi_detik']} detik dengan memori puncak sekitar "
            f"{koma(f['ram_mb'] / 1024, 1)} GB pada {f['cpu']}, tanpa GPU.",
            "**Keandalan dan portabilitas:** *job* diulang bila gagal, setiap layanan punya pemeriksaan kesehatan, "
            "seluruh layanan dijalankan dengan Docker Compose, dan basis data dicadangkan harian dalam bentuk terenkripsi.",
            "**Kegunaan:** tata letak responsif untuk ponsel 390 piksel dan desktop; teks berbahasa Indonesia; "
            "kontras warna memenuhi WCAG AA.",
        ]),
        ("h2", "6.4 Arsitektur Sistem"),
        ("p", "Gambar 2 memperlihatkan arsitektur GemaHutan. Antarmuka Next.js berkomunikasi dengan API FastAPI. "
              "API menyimpan data ke PostgreSQL dengan PostGIS, menyimpan audio ke MinIO, dan memasukkan *job* ke "
              "antrean Redis. *Worker* mengambil *job*, menjalankan inferensi di CPU, lalu menyimpan hasilnya. Alat perekam "
              "lapangan (Tahap 2 dan 3) digambarkan dengan garis putus; alat tersebut akan mengunggah melalui API "
              "yang sama."),
        ("fig", "docs/assets/diagrams/arsitektur.png", 13.5, "Arsitektur sistem GemaHutan"),
        ("h2", "6.5 Alur Pemrosesan Rekaman"),
        ("p", "Gambar 3 memperlihatkan dua belas tahap dari unggahan sampai verifikasi. Berkas divalidasi isinya "
              "sebelum disimpan. *Worker* menjalankan BirdNET dan pengklasifikasi lokal secara paralel, menggabungkan "
              "hasilnya, lalu menerapkan ambang per spesies dan penyaring deteksi lemah. Deteksi yang sudah "
              "diverifikasi ahli dapat menjadi bahan latih ulang, tetapi model baru hanya dipasang setelah lolos "
              "gerbang evaluasi."),
        ("fig", "docs/assets/diagrams/alur_pemrosesan.png", 12.0, "Alur pemrosesan rekaman dari unggah sampai verifikasi"),
        ("h2", "6.6 Rancangan Basis Data"),
        ("p", "Basis data terdiri atas sepuluh tabel (Gambar 4). Tabel *recordings* dan *detections* menjadi pusat "
              "data: satu rekaman memiliki banyak deteksi, satu *job*, dan satu baris indeks *soundscape*. Kolom "
              "*location* pada tabel *sites* memakai tipe geometri PostGIS untuk kebutuhan peta."),
        ("fig", "docs/assets/diagrams/erd.png", 13.0, "Rancangan basis data (ERD)"),

        ("h1", "7. IMPLEMENTASI PERANGKAT LUNAK"),
        ("h2", "7.1 Teknologi"),
        ("tbl", "Teknologi yang digunakan", ["Lapisan", "Teknologi"], [
            ["Antarmuka", "Next.js 15, React 19, TypeScript, Tailwind CSS 4, daisyUI 5, TanStack Query, MapLibre GL, WaveSurfer.js, Recharts"],
            ["API", "Python 3.11, FastAPI, Pydantic, SQLAlchemy, Alembic"],
            ["Antrean dan *worker*", "Redis 7, ARQ"],
            ["Data dan berkas", "PostgreSQL 16 dengan PostGIS 3.4; MinIO (kompatibel S3)"],
            ["Machine learning", "BirdNET-Analyzer 2.4 (TFLite, CPU), scikit-learn (Pedregosa *et al.*, 2011), librosa, "
                                 "scikit-maad (Ulloa *et al.*, 2021)"],
            ["Lokalisasi", "NumPy: GCC-PHAT, pencocokan arah, triangulasi kisi (modul *ml/localization.py*)"],
            ["Operasi", "Docker Compose, Caddy (HTTPS), GitHub Actions; server awan UpCloud (Singapura) 4 vCPU AMD EPYC, RAM 8 GB, disk 100 GB, USD 50 per bulan, di https://gemahutan.site"],
        ], [3.5, 12.5]),
        ("h2", "7.2 Model Deteksi Spesies"),
        ("p", "Audio diubah menjadi mono 48 kHz dan dipotong per jendela 3 detik. Jalur A menjalankan BirdNET "
              "secara langsung (*zero-shot*) dengan filter wilayah dari koordinat lokasi. Jalur B mengambil "
              "*embedding* 1.024 dimensi dari lapisan akhir BirdNET, lalu mengklasifikasikannya dengan regresi "
              "logistik multikelas untuk 25 spesies ditambah satu kelas negatif. Keyakinan dikalibrasi dengan "
              "*temperature scaling* dan bias per kelas (Guo *et al.*, 2017), dan setiap spesies memiliki ambang "
              "sendiri. Dalam perbandingan internal, regresi logistik mengungguli MLP dua lapis dan menghasilkan "
              "deteksi palsu lebih sedikit, sejalan dengan temuan bahwa *embedding* BirdNET sudah cukup untuk "
              "pengklasifikasi linear (Ghani *et al.*, 2023). Hasil kedua jalur digabung, lalu deteksi yang lebih pendek "
              "dari 1 detik dibuang, dan deteksi berkeyakinan di bawah 0,5 harus muncul minimal dua kali."),
        ("p", "Data latih berjumlah 8.102 klip (2.490 klip spesies target dan 5.612 klip negatif) dari Xeno-canto "
              "(Xeno-canto Foundation, 2026), iNatSounds (Chasmai *et al.*, 2024), SEA-Bird (Zabidi, 2025), dan Indonesian Bird Sounds "
              "(ULM Data Science Lab, 2025); dua himpunan data terakhir juga berasal dari rekaman Xeno-canto. Klip berlisensi *no-derivatives* (ND) "
              "dikeluarkan. Daftar spesies target ada pada Tabel 5."),
        ("p", "Dari audio yang sama *worker* menghitung indeks *soundscape* ACI, NDSI, ADI, dan BI dengan scikit-maad "
              "(Pieretti, Farina dan Morri, 2011; Kasten *et al.*, 2012; Villanueva-Rivera *et al.*, 2011; "
              "Boelman *et al.*, 2007) sebagai gambaran aktivitas akustik lokasi, yang ditampilkan untuk admin dan "
              "peneliti."),
    ]
    sp = f["spesies"]
    setengah = (len(sp) + 1) // 2
    baris = []
    for i in range(setengah):
        kiri = sp[i]
        kanan = sp[i + setengah] if i + setengah < len(sp) else None
        baris.append([f"*{kiri['scientific_name']}*", kiri["common_name_id"],
                      f"*{kanan['scientific_name']}*" if kanan else "", kanan["common_name_id"] if kanan else ""])
    b.append(("tbl", "Dua puluh lima spesies burung target pengklasifikasi lokal",
              ["Nama ilmiah", "Nama Indonesia", "Nama ilmiah", "Nama Indonesia"], baris, [4.3, 3.7, 4.3, 3.7]))

    b += [
        ("h2", "7.3 Perkiraan Lokasi dan Simulasinya"),
        ("p", "Perkiraan lokasi memakai selisih waktu tiba suara (*time difference of arrival*, TDOA) di antara "
              "mikrofon (Rhinehart *et al.*, 2020). Untuk setiap pasangan mikrofon *i* dan *j* pada satu alat, "
              "selisih waktu dihitung dengan korelasi silang tergeneralisasi berbobot fase (GCC-PHAT) (Knapp dan "
              "Carter, 1976), dengan *X* spektrum sinyal, ∗ konjugat kompleks, dan *F*⁻¹ transformasi Fourier balik:"),
        ("eq", "*R*ᵢⱼ(τ) = *F*⁻¹ [ *X*ᵢ(*f*) *X*ⱼ∗(*f*) / |*X*ᵢ(*f*) *X*ⱼ∗(*f*)| ],    τ̂ᵢⱼ = arg maks |*R*ᵢⱼ(τ)|", 1),
        ("p0", "Arah datang θ dari satu alat dipilih sebagai sudut yang selisih waktu teoretisnya paling cocok "
               "dengan hasil ukur, dengan **p** posisi mikrofon, **u**(θ) vektor satuan arah, dan *c* = 343 m/s:"),
        ("eq", "θ̂ = arg min Σ₍ᵢ,ⱼ₎ ( τ̂ᵢⱼ − (**p**ⱼ − **p**ᵢ) · **u**(θ) / *c* )²,    0° ≤ θ < 360°", 2),
        ("p0", "Jarak kasar diperkirakan dari penurunan level suara terhadap level acuan *L*₀ pada jarak *r*₀ yang "
               "sudah dikalibrasi, sedangkan posisi didapat dengan mencari titik pada kisi yang paling sesuai dengan "
               "arah dari *K* alat:"),
        ("eq", "*r* = *r*₀ · 10 ^ [ (*L*₀ − *L*) / 20 ]", 3),
        ("eq", "(*x̂*, *ŷ*) = arg min Σₖ ∠( **u**(θ̂ₖ), (*x* − *x*ₖ, *y* − *y*ₖ) )²", 4),
        ("p", f"Persamaan (1) sampai (4) diuji dengan simulasi: {len(f['sim']['alat'])} alat virtual, masing-masing "
              "larik 4 mikrofon bujur sangkar 0,5 m, dipasang membentuk segitiga sekitar 120 m, dan "
              f"{f['sim']['n_sumber']} sumber suara buatan ditaruh acak di area pantau. Galat posisi median "
              + _sim(f) + " (Gambar 5). Angka ini adalah batas atas mutu karena sinyal buatan tidak mengandung gema "
              "dan jam alat dianggap sinkron. Fitur simulasi di aplikasi memakai modul yang sama, sehingga petugas "
              "dapat mencoba tata letak alat sebelum alat sungguhan dibeli dan dipasang."),
        ("fig", "docs/assets/diagrams/simulasi_lokasi.png", 14.0,
         "Simulasi perkiraan lokasi: (a) arah dari tiga alat virtual berpotongan di sumber suara, "
         "(b) galat posisi pada beberapa tingkat derau"),
        ("h2", "7.4 Hasil Evaluasi Model"),
        ("p", "Tabel 6 merangkum hasil evaluasi model yang terpasang di produksi. Selang kepercayaan 95% dihitung "
              "dengan *bootstrap*. Pada validasi silang, sampel diambil per perekam; pada uji independen, per klip."),
        ("tbl", "Hasil evaluasi model produksi (regresi logistik v3)", ["Pengujian", "Data", "Hasil"], [
            ["Validasi silang bersarang, per perekam", f"{cv['n']} klip, {cv['grup']} perekam",
             f"F1 makro {koma(cv['f1'])} ({_ik(*cv['f1_ci'])}); akurasi {koma(cv['acc'])} ({_ik(*cv['acc_ci'])})"],
            ["Sama, memakai ambang per spesies", f"{cv['n']} klip",
             f"presisi {koma(cv['p_ambang'])}; *recall* {koma(cv['r_ambang'])}"],
            ["Uji independen, negara lain", f"{ind['n']} klip", f"akurasi {koma(ind['acc'])} ({_ik(*ind['ci'])}); F1 makro {koma(ind['f1'])}"],
            ["Menyeluruh: semua rekaman target", f"{e['target'][2]} berkas",
             f"presisi {koma(e['target'][0])}; *recall* {koma(e['target'][1])}"],
            ["Menyeluruh: Xeno-canto kualitas rendah", f"{e['xc'][2]} berkas", f"presisi {koma(e['xc'][0])}; *recall* {koma(e['xc'][1])}"],
            ["Menyeluruh: rekaman ponsel iNaturalist", f"{e['inat'][2]} berkas", f"presisi {koma(e['inat'][0])}; *recall* {koma(e['inat'][1])}"],
            ["Menyeluruh: uji independen", f"{e['ind'][2]} berkas", f"presisi {koma(e['ind'][0])}; *recall* {koma(e['ind'][1])}"],
            ["Menyeluruh: spesies pengecoh", f"{e['peng_n']} berkas",
             f"{e['peng_fp']} berkas ({round(100 * e['peng_fp'] / e['peng_n'])}%) memicu deteksi palsu; "
             f"{koma(e['fp_menit'], 2)} per menit"],
            ["Kecepatan dan memori", "rekaman 60 menit",
             f"{f['latensi_detik']} detik; memori puncak {koma(f['ram_mb'] / 1024, 1)} GB (CPU)"],
        ], [5.4, 3.4, 7.2]),
        ("p", f"Gambar 6 menunjukkan F1 per spesies. Spesies terkuat adalah *{f['terkuat'][0]}* "
              f"(F1 {koma(f['terkuat'][1], 2)}), sedangkan yang terlemah adalah "
              + ", ".join(f"*{n}* ({koma(v, 2)})" for n, v in f["terlemah"])
              + ". Kelemahan utama model adalah deteksi palsu pada spesies di luar daftar target. "
              "Karena itu deteksi diperlakukan sebagai kandidat, dan hasil verifikasi ahli dipakai sebagai bahan "
              "latih ulang yang hanya dipasang setelah lolos gerbang evaluasi."),
        ("fig", "docs/assets/diagrams/f1_per_spesies.png", 10.5,
         "F1 per spesies pada validasi silang bersarang (batang terang: F1 di bawah 0,55)"),
        ("h2", "7.5 Pengujian dan Validasi Pengguna"),
        ("p", "Setiap kebutuhan fungsional diuji secara *black-box* lewat peramban (Chromium, layar ponsel dan "
              "desktop) memakai akun tiap peran, pada lingkungan uji yang menjalankan kode yang sama dengan "
              "https://gemahutan.site (Tabel 7). Bukti tangkapan layar dan berkas hasilnya disimpan di repositori. Hasil validasi pengguna dirangkum pada Tabel 8. Skor SUS 77,0 berada pada kategori "
              "*Good* (Bangor, Kortum dan Miller, 2009). Kesulitan yang paling sering muncul adalah menemukan menu "
              "simulasi lokasi dan laporan, serta alur unggah pada percobaan pertama; ketiganya sudah "
              "ditindaklanjuti pada iterasi yang sama: formulir unggah diberi langkah bernomor, serta tautan ke "
              "simulasi dan laporan bulanan ditambahkan di dasbor, halaman rekam, dan detail rekaman."),
        ("tbl", "Hasil pengujian *black-box* per kebutuhan fungsional (5 Oktober 2026)", ["Kode", "Skenario uji", "Hasil"], [
            ["KF-01", "Admin mengundang akun; petugas membuat sandi dari tautan lalu masuk",
             "Lulus (surel uji dicatat server karena SMTP lokal kosong)"],
            ["KF-02", "Admin menambah lokasi, perangkat 4 kanal, dan status prioritas spesies; *ranger* mencoba hal yang sama",
             "Lulus. Admin berhasil; *ranger* ditolak (403)"],
            ["KF-03", "*Ranger* merekam 30 detik dari ponsel dan mengunggah 5 berkas sekaligus",
             "Lulus. Rekaman 30 detik tersimpan dan diproses; 5 berkas terunggah sekaligus"],
            ["KF-04, 05", "Status berubah otomatis sampai selesai; deteksi dan skor tampil",
             "Lulus. 6 rekaman selesai; skor per spesies tampil"],
            ["KF-06", "*Ranger* membuka rekaman milik akun lain lewat alamat langsung",
             "Lulus. API menjawab 404, isi tidak tampil"],
            ["KF-08, 09", "Peneliti memverifikasi lalu mengekspor CSV; *ranger* tidak bisa mengekspor",
             "Lulus. CSV terunduh; *ranger* tidak melihat tombol ekspor dan API menolaknya (403)"],
            ["KF-10", "Deteksi spesies prioritas memicu peringatan; lokasi tepat tidak terbuka bagi *ranger*",
             "Lulus. Elang Bondol (skor 0,998) memicu peringatan; *ranger* tidak menerima koordinat lokasi"],
            ["KF-11", "Tiga alat virtual menghasilkan area perkiraan yang memuat sumber",
             "Lulus. Galat 1,0 m di dalam radius area 6,0 m"],
            ["KF-07", "Laporan bulanan dicetak ke PDF dari peramban",
             "Belum. Laporan ringkas bisa dicetak; versi bulanan per kawasan sedang dikerjakan"],
            ["KF-12", "Jejak audit tindakan penting; pemangkasan audio setelah 90 hari",
             "Sebagian. Masuk, undangan, peran, dan verifikasi tercatat; pemangkasan belum dibangun"],
        ], [1.8, 6.6, 7.6]),
        ("tbl", "Hasil validasi pengguna", ["Validasi", "Pelaksanaan", "Hasil"], [
            ["Rekaman lapangan", "[PERLU DIISI: lokasi, tanggal, durasi]", "[PERLU DIISI: jumlah deteksi; persentase yang benar setelah didengarkan ulang]"],
            ["Uji kegunaan SUS", "5 mahasiswa Kehutanan Universitas Lampung (R01 sampai R05), mengerjakan 5 tugas peran *ranger* dan 5 tugas peran peneliti, 5 Oktober 2026", "Skor SUS rata-rata 77,0 (rentang 72,5 sampai 80,0), kategori *Good*; 48 dari 50 tugas selesai (96%); bantuan paling sering untuk menemukan simulasi lokasi dan menu laporan"],
        ], [3.2, 5.4, 7.4]),
        ("h2", "7.6 Keamanan dan Jaminan Mutu"),
        ("bul", [
            "Token akses JWT berlaku 30 menit dan token penyegar dirotasi. Keduanya dicabut saat pengguna keluar. "
            "Tautan atur ulang sandi bersifat sekali pakai dan disimpan dalam bentuk hash SHA-256.",
            "Pembatas laju per alamat IP (baca 300, tulis 60, dan unggah 20 permintaan per menit). Login dikunci "
            "sementara setelah 5 kali gagal dalam satu menit.",
            "Isi berkas diperiksa dengan ffprobe sebelum disimpan, bukan hanya ekstensinya. Berkas audio hanya "
            "dapat diambil lewat API yang meminta token.",
            "Lokasi tepat spesies prioritas hanya untuk admin dan peneliti; akun tamu halaman depan hanya dapat membaca "
            "rekamannya sendiri dan dibatasi 10 unggahan per 24 jam.",
            "Mode produksi menolak berjalan jika rahasia masih bernilai contoh dan menutup dokumentasi API publik. "
            "Basis data dicadangkan harian dan terenkripsi.",
            f"Mutu dijaga oleh {sum(f['test'].values())} kasus uji otomatis dan dua skrip audit: 22 pemeriksaan "
            "mutu model dan 14 pemeriksaan kesiapan penerapan.",
        ]),
    ]
    return b
