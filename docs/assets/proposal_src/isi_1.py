"""Isi proposal bagian 1: cover, judul, latar belakang, tujuan-manfaat, batasan, metodologi."""
from data import koma

JUDUL = ("GemaHutan: Deteksi Suara dan Perkiraan Lokasi Burung Langka "
         "untuk Petugas Konservasi Hutan Indonesia")


def isi(f):
    cv, e = f["cv"], f["e2e"]
    b = [("cover", {"logo": "docs/assets/logo_gunadarma.png", "baris": [
        ("PROPOSAL", 16, True, 6),
        (JUDUL, 14, True, 14),
        ("IMG:apps/web/public/icon-512.png|2.6", None, None, 14),
        ("JENIS LOMBA", 12, True, 2),
        ("SOFTWARE DEVELOPMENT", 12, False, 20),
        ("LOGO", None, None, 0),
        ("DISUSUN OLEH: KATA AJRA BISA NGODING WALAUPUN TOKEN HABIS", 12, True, 8),
        ("ARTYA EPRILIANI\t10124205", 12, False, 2),
        ("AZRA HUDAYA\t50423244", 12, False, 48),
        ("UNIVERSITAS GUNADARMA", 12, True, 2),
        ("2026", 12, True, 0),
    ]}), ("pb",)]

    b += [
        ("h1", "1. JUDUL DAN NAMA PERANGKAT LUNAK"),
        ("p0", f"**Nama perangkat lunak:** GemaHutan. **Judul:** {JUDUL}."),
        ("p", "GemaHutan adalah ekosistem pemantauan suara hutan untuk **mendeteksi dan memperkirakan di mana "
              "burung langka berada**. Alat perekam di hutan menangkap suara, model kecerdasan artifisial mengenali spesiesnya, lalu "
              "arah dan jarak dari beberapa alat yang mendengar suara yang sama dipakai untuk memperkirakan "
              "lokasinya. Pengembangannya dibagi lima tahap (Bagian 5). Proposal ini membahas **Tahap 1, yaitu "
              "perangkat lunak**: aplikasi web untuk admin kawasan, peneliti, dan *ranger*, model deteksi 25 spesies "
              "burung Indonesia di atas BirdNET, verifikasi ahli, laporan bulanan, perlindungan lokasi spesies "
              "prioritas, dan simulasi perkiraan lokasi dengan alat virtual. Seluruh layanan berjalan di CPU tanpa "
              "GPU dan dapat diakses di https://gemahutan.site."),

        ("h1", "2. LATAR BELAKANG IDE PERANGKAT LUNAK"),
        ("p", "Indonesia mencatat 1.834 spesies burung per Januari 2026, 538 di antaranya endemis dan 159 berstatus "
              "terancam punah secara global (Burung Indonesia, 2026). Selain kehilangan habitat, burung Indonesia "
              "tertekan oleh penangkapan untuk perdagangan burung kicau. Survei lebih dari 3.000 rumah tangga di "
              "Jawa menunjukkan kebiasaan memelihara burung masih luas dan menjadi pendorong utama yang dikenal "
              "sebagai Krisis Burung Kicau Asia (Marshall *et al.*, 2020). Pengelola kawasan karena itu perlu tahu "
              "di mana spesies langka masih ada, dan informasi itu sendiri harus dijaga agar tidak jatuh ke tangan "
              "pemburu."),
        ("p", "Survei langsung membutuhkan tenaga ahli dan waktu lapangan yang panjang, serta kurang efektif untuk "
              "satwa yang lebih mudah didengar daripada dilihat (Sugai *et al.*, 2019). Perekam otomatis berbiaya "
              "rendah seperti AudioMoth (Hill *et al.*, 2019) dapat merekam berhari-hari, tetapi jam rekaman "
              "bertambah jauh lebih cepat daripada kemampuan manusia mendengarkannya (Gibb *et al.*, 2019; Stowell, "
              "2022). BirdNET mengenali ribuan spesies dari suara (Kahl *et al.*, 2021), dan *embedding*-nya dapat "
              "dipakai melatih pengklasifikasi ringan untuk spesies lokal (Ghani *et al.*, 2023). Jika beberapa perekam "
              "dengan jam yang tersinkron mendengar suara yang sama, selisih waktu tibanya dapat dipakai memperkirakan posisi "
              "sumber suara (Rhinehart *et al.*, 2020)."),
        ("p", "Perangkat yang ada umumnya menangani sebagian alur saja (Tabel 1). Bagi balai taman nasional atau "
              "BKSDA masih ada empat kesenjangan: model global belum diukur untuk spesies target Indonesia; rekaman, "
              "verifikasi ahli, peta, dan laporan dikerjakan terpisah oleh orang yang mampu memprogram; perkiraan "
              "lokasi dari beberapa perekam belum tersedia dalam alat kerja petugas; dan peta lokasi spesies langka "
              "tidak dilindungi sesuai peran pengguna."),
        ("tbl", "Perbandingan GemaHutan dengan perangkat yang sudah ada", ["Perangkat", "Fokus", "Yang belum dicakup untuk kebutuhan balai"], [
            ["BirdNET App (Kahl *et al.*, 2021)", "Identifikasi spesies per rekaman di ponsel",
             "Alur kerja tim, verifikasi ahli, laporan kawasan, perkiraan lokasi"],
            ["Arbimon (Aide *et al.*, 2013)", "Platform web pemantauan akustik dan pembuatan model",
             "Model siap pakai untuk spesies target Indonesia, perkiraan lokasi untuk petugas, perlindungan lokasi per peran"],
            ["Raven Pro (K. Lisa Yang Center for Conservation Bioacoustics, 2023), Kaleidoscope Pro (Wildlife Acoustics, 2026)", "Perangkat lunak desktop untuk analisis manual atau semi-otomatis",
             "Kerja bersama per peran, akses dari ponsel, laporan bulanan"],
            ["**GemaHutan**", "Alur utuh: rekam atau unggah, deteksi, verifikasi, laporan, simulasi lokasi",
             "Lokasi dari alat nyata baru di Tahap 3 (Bagian 5)"],
        ], [3.6, 5.2, 7.2]),
        ("p", "Ide ini sejalan dengan tema USB 2026 \"Ekosistem Digital untuk Masa Depan Indonesia yang Inklusif dan "
              "Berkelanjutan\" pada sektor lingkungan, serta mendukung Tujuan Pembangunan Berkelanjutan (TPB) 15 "
              "tentang ekosistem daratan."),

        ("h1", "3. TUJUAN DAN MANFAAT PENGEMBANGAN PERANGKAT LUNAK"),
        ("h2", "3.1 Tujuan"),
        ("num", [
            "Menyediakan alur kerja utuh untuk tiga peran dalam satu aplikasi web: rekam atau unggah, deteksi "
            "otomatis, verifikasi ahli, ekspor, dan laporan bulanan per kawasan.",
            "Mendeteksi 25 spesies burung Indonesia dengan pengklasifikasi lokal di atas BirdNET, lengkap dengan ambang "
            "keputusan per spesies dan angka mutu yang dapat diperiksa ulang.",
            "Melindungi spesies prioritas: penandaan dari daftar resmi IUCN (IUCN, 2026) dan Permen LHK P.106/2018 "
            "(Kementerian Lingkungan Hidup dan Kehutanan, 2018), lokasi tepat hanya untuk admin dan peneliti, "
            "serta peringatan surel ketika spesies prioritas terdeteksi.",
            "Menyiapkan perkiraan lokasi sebelum alat dipasang, melalui simulasi alat virtual di peta yang memakai "
            "metode yang sama dengan Tahap 3.",
            f"Berjalan pada perangkat umum tanpa GPU: rekaman 60 menit diproses sekitar {f['latensi_detik']} detik "
            f"pada {f['cpu']}.",
        ]),
        ("h2", "3.2 Manfaat"),
        ("bul", [
            "**Admin kawasan (balai atau BKSDA):** memantau keberadaan spesies per lokasi lewat dasbor, peta, dan "
            "laporan bulanan tanpa mendengarkan seluruh rekaman, serta mendapat peringatan saat spesies prioritas "
            "terdengar.",
            "**Peneliti dan ahli burung:** memverifikasi deteksi, mengekspor data terverifikasi (CSV atau JSON), dan "
            "memeriksa ulang setiap angka mutu model.",
            "**Ranger dan relawan:** merekam dari ponsel melalui peramban tanpa memasang aplikasi, melihat hasil "
            "rekamannya sendiri, dan berlatih membaca perkiraan lokasi dengan simulasi.",
            "**Keberlanjutan:** seluruh layanan berjalan dengan komponen sumber terbuka di satu server awan tanpa "
            "GPU (4 vCPU, RAM 8 GB, disk 100 GB) dengan biaya USD 50 per bulan untuk satu kawasan, sehingga terjangkau "
            "bagi instansi kecil. Deteksi yang diverifikasi ahli menjadi bahan latih ulang, jadi model membaik "
            "seiring pemakaian.",
        ]),

        ("h1", "4. BATASAN PERANGKAT LUNAK YANG DIKEMBANGKAN"),
        ("bul", [
            "**Tahap:** proposal ini mencakup Tahap 1 (perangkat lunak). Alat perekam, pengujian lapangan resmi, "
            "dan perkiraan lokasi dari alat nyata adalah Tahap 2 sampai 5.",
            "**Platform:** aplikasi web untuk peramban desktop dan ponsel (PWA). Tidak ada aplikasi Android native. "
            "Rekaman dari alat apa pun diunggah sebagai berkas, asalkan waktu rekam dan posisi alat tercatat.",
            "**Cakupan spesies:** pengklasifikasi lokal mengenali 25 spesies burung (Tabel 5). Spesies ini dipilih dari "
            "ketersediaan rekaman berlisensi terbuka, sehingga sebagian besar adalah burung umum yang datanya cukup untuk "
            "membangun dan menguji alur deteksi. Spesies langka target kawasan ditambahkan pada Tahap 2 dari rekaman "
            "lapangan yang diverifikasi pakar. Sebelum itu, spesies di luar daftar hanya dikenali oleh BirdNET dengan "
            "ambang umum. Satwa selain burung belum menjadi target.",
            f"**Mutu yang sudah terukur:** pada uji menyeluruh, {e['peng_fp']} dari {e['peng_n']} rekaman spesies "
            f"non-target ({round(100 * e['peng_fp'] / e['peng_n'])}%) masih memicu deteksi palsu, dan *recall* pada "
            f"rekaman ponsel {koma(e['inat'][1], 2)}. Karena itu setiap deteksi otomatis diperlakukan sebagai "
            "kandidat yang perlu diverifikasi.",
            "**Perkiraan lokasi:** di Tahap 1 hanya berupa simulasi dengan sinyal buatan tanpa gema. Rekaman nyata "
            "membutuhkan alat dengan minimal 2 kanal dan jam yang tersinkron.",
            "**Teknis:** antarmuka berbahasa Indonesia; unggah 1 sampai 20 berkas, maksimal 200 MB per berkas; satu "
            "kawasan per server; belum ada mode luring. BirdNET berlisensi CC BY-NC-SA 4.0, sehingga pemakaian "
            "dibatasi untuk tujuan non-komersial.",
        ]),

        ("h1", "5. METODOLOGI PENGEMBANGAN PERANGKAT LUNAK"),
        ("p", "Produk dikembangkan dalam lima tahap (Gambar 1). Tahap 1 menyiapkan perangkat lunak dan metodenya, "
              "sehingga saat alat perekam dipasang di Tahap 2 dan 3, pengelola kawasan tinggal menghubungkan data "
              "alat ke sistem yang sudah teruji."),
        ("fig", "docs/assets/diagrams/tahapan.png", 16.0,
         "Lima tahap pengembangan GemaHutan dan linimasa Tahap 1"),
        ("p", "Di dalam Tahap 1 dipakai model proses inkremental dan iteratif (Pressman dan Maxim, 2020). Setiap "
              "iterasi menghasilkan versi yang berjalan dan telah diuji, karena mutu model deteksi baru diketahui "
              "setelah diukur. Setiap iterasi terdiri atas lima langkah:"),
        ("num", [
            "**Analisis kebutuhan:** prioritas dari kebutuhan peran pengguna dan hasil audit iterasi sebelumnya.",
            "**Desain:** arsitektur, skema basis data, alur pemrosesan, dan rancangan antarmuka (Bagian 6 dan 8).",
            "**Implementasi:** kode dikelola dengan git; sejak " + _tanggal(f["mulai"]) + " tercatat "
            f"{f['jumlah_commit']} *commit* di repositori pengembangan; repositori publik berisi salinan bersih kode yang sama.",
            f"**Pengujian:** {sum(f['test'].values())} kasus uji otomatis (API {f['test']['API']}, *worker* "
            f"{f['test']['worker']}, ML {f['test']['ML']}, web {f['test']['web']}), integrasi berkelanjutan "
            "(GitHub Actions), pengujian *black-box* per kebutuhan fungsional (Tabel 7), dan uji kegunaan.",
            "**Evaluasi:** hasil dibandingkan dengan target, lalu keputusan dan koreksi dicatat.",
        ]),
        ("p", "Model deteksi dievaluasi dengan protokol yang menghindari angka terlalu optimistis: validasi silang "
              f"bersarang 5 lipatan yang dikelompokkan per perekam ({cv['grup']} perekam), uji independen pada "
              f"{f['ind']['n']} klip dari negara lain, dan uji menyeluruh jalur produksi pada {e['n']} berkas, "
              "termasuk rekaman ponsel dan spesies pengecoh. Model baru hanya dipasang jika lolos gerbang evaluasi."),
        ("p", "Validasi dengan pengguna dilakukan dengan dua cara. Pertama, perekaman lapangan "
              "[PERLU DIISI: durasi, lokasi, dan tanggal perekaman] yang setiap deteksinya diperiksa ulang dengan "
              "mendengarkan potongan suaranya. Kedua, uji kegunaan dengan *System Usability Scale* (SUS) "
              "(Brooke, 1996) versi bahasa Indonesia (Sharfina dan Santoso, 2016) pada 5 Oktober 2026 dengan lima "
              "mahasiswa Kehutanan Universitas Lampung yang mengerjakan tugas sesuai perannya; skor ditafsirkan "
              "dengan skala ajektif Bangor, Kortum dan Miller (2009). Penilaian oleh pakar ornitologi dijadwalkan "
              "pada Tahap 2 bersama kawasan mitra."),
    ]
    return b


def _tanggal(iso):
    th, bl, hr = iso.split("-")
    bulan = ["Januari", "Februari", "Maret", "April", "Mei", "Juni", "Juli", "Agustus", "September",
             "Oktober", "November", "Desember"][int(bl) - 1]
    return f"{int(hr)} {bulan} {th}"
