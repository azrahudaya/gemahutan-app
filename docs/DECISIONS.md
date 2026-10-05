# Keputusan Teknis -- GemaHutan

> Setiap keputusan dicatat: apa, kenapa, dan apa yang perlu diubah kalau diarahkan lain.

## Asumsi Default (dari Master Prompt)

| Keputusan | Alasan | Ubah kalau |
|-----------|--------|------------|
| Nama produk: GemaHutan | Sesuai brief kompetisi | Tim punya nama lain |
| Bahasa UI: Indonesia, toggle EN parsial | Target user ranger/peneliti Indonesia | Lomba minta full EN |
| Auth: email+password (Argon2), JWT | Sederhana, tanpa OAuth dependency | Butuh SSO/OAuth |
| Repo publik `azrahudaya/gemahutan` (snapshot bersih), riwayat kerja di repo privat `gemahutan-arsip` | Juri bisa membaca kode tanpa riwayat berisi data mentah | - |
| Lisensi MIT untuk kode sendiri | Permisif, standar lomba | Ada ketentuan lain |
| Stack: Next.js 15 + FastAPI + PostgreSQL + Redis + MinIO | Satu bahasa Python untuk API+ML, Next.js untuk SSR+PWA | - |
| Tema terang hijau daisyUI `gemahutan` (diganti 3 Okt 2026, dulu dark mode biru) | Lihat `DESIGN.md` | - |
| Tile peta gratis (tanpa API key) | Tidak butuh kredensial pihak ketiga | Ada MapTiler/Mapbox key |
| Tim: kata ajra bisa ngoding walaupun token habis | Sudah ada | - |
| Ketentuan lomba: asumsi submit = repo + README + video + slide | PDF ketentuan tidak ditemukan di mesin | Dapat file PDF |

## Single-tenant (keputusan operasional)

**Keputusan:** GemaHutan berjalan sebagai single-tenant, satu kawasan
konservasi per server. Bukan multi-tenant. Multi-kawasan baru di Tahap 5
(lihat `docs/VISI_DAN_RUANG_LINGKUP.md`).

- Admin dan peneliti melihat lintas pengguna (recording, detection, jobs, exports, stats).
- Ranger hanya melihat data miliknya sendiri, lewat filter `uploaded_by`
  di tiap query ORM (`app/services/access.py:recording_scope`).
- Lokasi (`sites`) tetap dipakai bersama, bukan per-tenant, karena satu
  kawasan punya banyak titik pantau yang dipakai banyak ranger.

**Justifikasi:** lebih aman untuk memulai dari satu organisasi. Pemisahan
tenant membawa overhead tambahan: schema migrasi, isolasi data, billing,
sampai audit log per-organisasi. Untuk satu kawasan konservasi, menambah
layer itu hanya memperbesar permukaan serangan tanpa manfaat yang
terukur sekarang.

**Batasan eksplisit:** bila GemaHutan dipakai multi-kawasan di fase
berikutnya, keputusan ini harus dibalik dan `recording_scope` ditambah
filter `organization_id` atau setara. Audit ulang wajib dilakukan:
pengujian object-level authorization lintas akun tidak cukup lagi,
harus lintas organisasi.

**Verifikasi:** `apps/api/tests/test_authorization_phase2.py` (4 kasus)
menjamin ranger tidak dapat membaca data ranger lain; admin tetap 200;
tanpa token ditolak 401 untuk jobs, batches, exports, stats.

## Keputusan produk 3 Oktober 2026

Ditetapkan pemilik produk. Rinciannya di `docs/VISI_DAN_RUANG_LINGKUP.md`, ringkasnya:

| Keputusan | Alasan |
|---|---|
| Pengguna adalah petugas konservasi (admin kawasan, peneliti, ranger), bukan masyarakat umum | Fitur dinilai dari kebutuhan lapangan dan kantor balai |
| Aplikasi petugas dibuka dengan login per peran; halaman depan menampilkan tombol Masuk dan "Coba contoh" kecil | Versi kunci hanya cocok untuk juri, bukan untuk petugas |
| Akun dibuat admin lewat undangan email, pendaftaran mandiri tetap tertutup | Akun petugas harus dikenali instansinya |
| Tidak ada aplikasi Android native | Web di peramban HP cukup; tumpuan visi ada di alat perekam yang dipasang |
| Tidak ada data demo di server produksi | Server hanya berisi data asli petugas |
| Ranger: rekam, unggah, hasil rekamannya sendiri, simulasi lokasi. Tanpa dashboard, ekspor, Model, Perangkat | Ranger butuh alat kerja, bukan analisis kawasan |
| Spesies prioritas dari IUCN CR/EN/VU dan Permen LHK P.106/2018, admin boleh menambah | Daftar resmi, bisa disesuaikan kawasan |
| Lokasi tepat spesies prioritas hanya untuk admin dan peneliti | Mencegah informasi jatuh ke pemburu. Ini membalik catatan lama "pengaburan koordinat bukan kebutuhan" di `docs/arsip/ARSITEKTUR_LENGKAP.md` |
| Peringatan spesies prioritas lewat email | Push Android gugur bersama aplikasinya |
| Email aplikasi dan notifikasi server memakai Gmail yang sama (App Password di server) | Satu kredensial untuk dikelola |
| Laporan bulanan per kawasan | Sesuai siklus pelaporan balai |
| Audio penuh 90 hari, lalu hanya potongan sekitar deteksi | Cukup untuk verifikasi, hemat disk |
| Alat perekam belum dipilih, sistem netral perangkat | Belum ada keputusan perangkat keras |
| Deteksi suara ancaman masuk Tahap 4, bukan sekarang | Butuh data dan model terpisah |
