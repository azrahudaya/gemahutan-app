> **Arsip, tidak berlaku lagi.** Dipindahkan ke `docs/arsip/` pada 3 Oktober 2026. Acuan yang
> berlaku: `docs/VISI_DAN_RUANG_LINGKUP.md`. Isi di bawah boleh dibaca untuk sejarah, tetapi
> jangan dijadikan dasar tugas.

# Rencana Eksekusi 30 Hari, 23 September - 22 Oktober 2026

Disusun setelah audit penuh 23 September. Batas keras: **seleksi
administrasi 10 Oktober** (17 hari dari sekarang). Seleksi lomba
presentasi 22 Oktober (29 hari). Penyerahan aplikasi final 9
November (47 hari), final 19 November (57 hari).

Prinsip: selesaikan blocker lisensi + reliability + web dalam 4
minggu. Sisakan buffer untuk lomba. Tidak ada kerjaan yang
"menunggu sampai akhir".

## Minggu 0 (23-29 Sept): blocker satu hari

Satu hari kerja, semua selesai sebelum weekend.

### Hari 1 (Rabu 23 Sept) - blocker harian
1. **Saring ND dari manifest**
   ```bash
   cd ~/Projects/gemahutan
   python3 -c "
   import csv
   keep=[]
   with open('ml/data/manifest.csv') as f:
       for row in csv.DictReader(f):
           if 'nd' in (row.get('license') or '').lower(): continue
           keep.append(row)
   with open('ml/data/manifest.csv','w',newline='') as f:
       w=csv.DictWriter(f, fieldnames=keep[0].keys())
       w.writeheader(); w.writerows(keep)
   print(f'kept={len(keep)}')
   "
   python3 ml/data/prepare.py
   ```
2. **Re-embed dan latih ulang**: `python3 ml/data/extract_embeddings.py` lalu `python3 ml/train.py --epochs 300 --hidden 256 --lr 0.001 --seed 42 --resume`. Catat val_acc dan test_acc baru. Estimasi: turun 0.01-0.03 karena data lebih bersih dan lebih sedikit (924 vs 1370 klip).
3. **Sync thresholds**: `make sync-thresholds`. Pastikan tidak ada drift.
4. **Fix FK + transaction abort di worker**
   ```python
   # apps/worker/worker.py, bungkus setiap insert acoustic_indices
   try:
       session.add(recording); session.flush()
       session.add(acoustic_indices); session.commit()
   except IntegrityError:
       session.rollback(); raise
   ```
5. **Guard noverlap**: `apps/worker/worker.py:415`, tambahkan `noverlap = min(nperseg // 2, max(1, nperseg - 1))`.
6. **Hapus checkpoints eksperimen**: `rm -rf ml/checkpoints_aug60 ml/checkpoints_aug120 ml/checkpoints_aug180 ml/checkpoints_augft`. Simpan `ml/checkpoints_aug/` saja kalau masih dipakai eksperimen.
7. **Ganti password admin**: edit `apps/api/app/seed.py` line 178, ganti `"admin123"` jadi placeholder `"GANTI-SETIAP-DEPLOY"`. Tambah validasi startup: `if password == "GANTI-SETIAP-DEPLOY" and ENV == production: raise`. Commit terpisah.
8. **`ALLOW_REGISTRATION=false`**: edit `apps/api/app/config.py`, default false. Deploy ulang.

### Hari 2 (Kamis 24 Sept) - reliability hardening
1. **Cek semua job yang gagal**: retry manual via `/api/v1/jobs/{id}/retry`. Pastikan FK fix tidak meninggalkan yatim.
2. **Audit Caddyfile** untuk HSTS, CSP, X-Frame-Options.
3. **Probe ulang otorisasi** lintas akun untuk `/jobs`, `/batches`, `/stats`, `/exports`. Dokumentasikan keputusan single-tenant di `docs/DECISIONS.md`.
4. **Audit log** untuk perubahan peran: tambah tabel `audit_log` + endpoint `GET /api/v1/audit` (admin only).
5. **Cek `npm audit` dan `pip-audit`** setelah lockfile dipulihkan.

### Hari 3 (Jumat 25 Sept) - test ulang semua
1. Test API di database bersih: 57 lulus (sama seperti 21 Sept).
2. Test worker: 25 lulus.
3. `verify_features.py`: target 28/28 lulus.
4. `security_check.py`: 6/6 lulus.
5. `tsc --noEmit`: bersih.
6. Update `docs/PROGRESS.md` dengan hasil.

## Minggu 1 (28 Sept - 4 Okt): Web core + proposal

### Senin 28 Sept - Scaffold web
- Buat folder `apps/web` dari nol (Next.js 15 App Router + TS + Tailwind + shadcn/ui).
- Tambah service `web` ke `docker-compose.yml` dan `deploy/docker-compose.prod.yml`.
- Dockerfile web multi-stage build.
- AppShell dengan sidebar + top bar konten, dark sesuai `DESIGN.md`.
- Setup `PUBLIC_API_URL`, auth context, token refresh interceptor.
- Build image, `docker compose up -d --force-recreate web`, verifikasi `curl -I http://localhost:3001`.

### Selasa 29 Sept - Halaman publik + otentikasi
- Landing (`/`) mengikuti `docs/USERFLOW_WEB.md` section 3: hero, alur kerja, CTA, footer. Pakai screenshot produk dari `docs/proposal/screenshots/` (bukan stok).
- Halaman `/masuk` dan `/daftar` (terakhir hanya muncul kalau `ALLOW_REGISTRATION=true`).
- Setup `react-hook-form` + `zod` untuk validasi.
- Test vitest untuk format util dan auth context.

### Rabu 30 Sept - Pendaftaran tutup
- Batas: ketua tim submit pendaftaran. Bukan kerjaan teknis.

### Kamis 1 Okt - Dasbor ranger
- `/dashboard` menjawab "apa yang gagal, apa yang perlu diulang".
- Tiga kartu stat nyata: rekaman gagal kemarin, batch in-progress, verifikasi menunggu.
- Daftar rekaman terbaru.
- Status worker (heartbeat dari `/api/v1/model/info`).
- Integrasi SSE untuk status job (EventSource + fallback polling 5 detik).

### Jumat 2 Okt - Daftar rekaman + detail
- `/rekaman`: tabel dengan filter lokasi, spesies, keyakinan, status, tanggal. Paginasi 20 per halaman.
- `/rekaman/{id}`: waveform (WaveSurfer.js), spektrogram (PNG endpoint), marker deteksi, klik marker lompat ke detik itu.
- Tampilkan `range_m` kalau ada.
- Tombol verifikasi (B/S/R dengan shortcut keyboard).
- Empty state yang benar.

### Sabtu 3 Okt - Proposal USB
- `docs/proposal/proposal.md` final: cover LAMPIRAN 1, judul, latar belakang, tujuan, batasan, metodologi, analisis kebutuhan, desain, implementasi, screenshot mockup, cara penggunaan, screenshot aplikasi, daftar pustaka.
- 20 halaman A4, spasi 1.5, font 12 Times New Roman.
- Angka diambil dari audit 23 Sept, bukan dari memori.

### Minggu 4 Okt - Unggah + rekam
- `/rekaman/baru`: pilih lokasi (wajib), perangkat (opsional), 1-20 berkas. Bilah progres per berkas.
- `/rekam`: MediaRecorder webm/opus 128 kbps. Paksa pilih lokasi dulu.
- Batch upload dengan `/api/v1/recordings/batch`.

## Minggu 2 (5-11 Okt): proposal final + admin pages

### Senin 5 Okt - Penyerahan proposal
- Submit `Proposal_SoftwareDevelopment_NamaTim_NamaProduk.pdf` ke panitia.

### Selasa 6 Okt - PPT + lokasi
- `docs/proposal/slide.md` jadi PPTX dengan python-pptx. Cover: anggota, nama produk, nama tim. 10 halaman.
- `/lokasi`: peta MapLibre + OSM, daftar, popup nama + habitat. Tambah/edit hanya admin (tombol admin disembunyikan untuk ranger).

### Rabu 7 Okt - Perangkat + kalibrasi
- `/perangkat`: daftar perangkat, kolom `mic_spacing_m`, `reference_distance_m`, `reference_level_db`.
- Form kalibrasi: admin isi setelah pengukuran lapangan, status berubah dari "Belum dikalibrasi" ke "Terkalibrasi 10 m, -23 dBFS".

### Kamis 8 Okt - Spesies + laporan
- `/spesies` daftar 25 spesies + sisanya dari BirdNET.
- `/spesies/{id}`: riwayat deteksi + grafik.
- `/laporan`: ringkasan siap cetak, tombol cetak peramban. Grafik matplotlib (data asli), bukan dekorasi.

### Jumat 9 Okt - Penyerahan revisi
- Submit revisi proposal + poster + software URL + surat pernyataan orisinalitas (LAMPIRAN 2) bermaterai.

### Sabtu 10 Okt - Seleksi administrasi
- Batas: panitia审核. Bukan kerjaan teknis, tapi standby kalau ada revisi.

## Minggu 3 (12-18 Okt): Polish + Android scaffold

### Senin 13 Okt - Technical meeting
- Batas: hadir technical meeting, catat pertanyaan juri.

### Selasa 14 Okt - Aksesibilitas audit
- Jalankan `audit_probe.py` di viewport 390 dan 1440.
- Lighthouse mobile target 90+ untuk Performance dan Accessibility.
- Kontras WCAG, fokus keyboard, tap target 44 px.
- Perbaiki yang gagal.

### Rabu 15 Okt - Fine-tune model (opsional)
- Kalau ada waktu: tambah 10-20 klip lapangan sendiri, re-embed, fine-tune dari `checkpoints/best_model.npz` dengan `--resume` dan lr lebih kecil (0,0001).
- Validasi: tangga degradasi + korpus lapangan. Bandingkan sebelum-sesudah per spesies.

### Kamis 16 Okt - Android scaffold
- `mkdir apps/android`. Kotlin + Compose Material3.
- Modul: `capture`, `queue` (Room), `sync` (Retrofit + OkHttp).
- Izin dan foreground service type `microphone`.
- Rekam 1 menit di emulator, lihat antrean terbentuk.

### Jumat 17 Okt - Android antrean + upload
- WorkManager upload dengan OkHttp resume.
- Checksum SHA-256 dicocokkan di server.
- Test end-to-end: rekam 5 menit, matikan proses, hidupkan, antrean pulih.

### Sabtu 18 Okt - Package Python
- `pyproject.toml` di root repo.
- Entry point: `gemahutan-train`, `gemahutan-eval`, `gemahutan-degrade`.
- `python -m build`, publish ke TestPyPI dulu.

## Minggu 4 (19-22 Okt): finalisasi + seleksi

### Senin 19 Okt - Buffer
- Fix bug dari audit, polish UI, update angka-angka di README.

### Selasa 20 Okt - Video YouTube
- Opening: logo USB 2026, logo Gunadarma, logo institusi (kalau ada), ikon aplikasi, nama produk, nama tim, anggota.
- 10 menit landscape 1920x1080.
- Status unlisted, judul `USB 2026 | Software Development | Nama Tim | Nama Produk`.
- Demo aplikasi yang jalan, angka riil.

### Rabu 21 Okt - Deploy publik
- `ALLOW_REGISTRATION=false`, ganti password demo, security headers (HSTS, CSP).
- HTTPS via Caddy + Let's Encrypt.
- Smoke test dari peramban publik.

### Kamis 22 Okt - Seleksi lomba
- Presentasi 10 menit, tanya jawab 15 menit.
- Bawa laptop dengan stack lokal hidup (backup).

## Setelah 22 Oktober

### 9 November - Penyerahan akhir
- `app/`, `PPT`, `manual book`. URL publik masih harus hidup.

### 19 November - Final
- Presentasi final. Stack hidup, demo jalan, angka konsisten dengan laporan.

## Ceklis harian

Tiap hari kerja sebelum commit:

- [ ] `docker compose ps` semua healthy
- [ ] `curl localhost:8000/healthz` 200
- [ ] `verify_features.py` 28/28 (atau 26/28 + planned)
- [ ] `security_check.py` 6/6
- [ ] Test API di db bersih: 57 lulus
- [ ] `tsc --noEmit` bersih (kalau ada perubahan web)

## Yang TIDAK dilakukan

- Tidak melatih ulang model dari awal (augmentasi terbukti memperburuk).
- Tidak menambah jumlah spesies dari 25 (perlu data lapangan yang banyak).
- Tidak deploy ke multi-region (single-tenant).
- Tidak menulis ulang `docs/AUDIT_AND_PLAN.md` (usang, biar).
- Tidak menambahkan fitur yang tidak diminta juri.

## Risiko

| Risiko | Mitigasi |
|---|---|
| Web tidak selesai dalam 3 minggu | Mulai hari ini, AppShell dulu, layar satu-satu |
| Model turun karena ND dibuang | Sudah dihitung, turun 0.01-0.03, masih di atas 0.65 |
| Disk penuh saat re-embed | Hapus checkpoints eksperimen dulu |
| Android tidak selesai | Aplikasi opsional, bukan syarat |
| Juri tanya hal tak terduga | Manual book dan PPT konsisten dengan aplikasi |
