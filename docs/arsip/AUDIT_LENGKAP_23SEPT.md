> **Arsip, tidak berlaku lagi.** Dipindahkan ke `docs/arsip/` pada 3 Oktober 2026. Acuan yang
> berlaku: `docs/VISI_DAN_RUANG_LINGKUP.md`. Isi di bawah boleh dibaca untuk sejarah, tetapi
> jangan dijadikan dasar tugas.

# Audit Penuh GemaHutan, 23 September 2026

Disusun dari runtime probe + source read, tanpa andalkan memori.
Stack hidup saat audit: api/worker/db/redis/minio healthy. Web tidak
ada di docker-compose.yml dan image tidak dibangun.

## Ringkasan satu layar

| Kategori | Temuan | Severity |
|---|---|---|
| Lisensi | 446/1370 (32.6%) klip ND bocor ke train/val/test | HIGH |
| Web | Image dan service tidak dibangun, folder source dihapus | BLOCKER |
| Authorization | jobs, batches, exports, stats tanpa filter ownership | HIGH |
| Worker | Bug FK `acoustic_indices` + transaction abort | MEDIUM |
| Worker | scipy `noverlap >= nperseg` pada audio pendek | MEDIUM |
| Worker | webm rekaman peramban corrupt | LOW (edge case) |
| Model | Precision-recall gap > 0.3 di 4 spesies | MEDIUM |
| Model | Confidence probability belum dikalibrasi | MEDIUM |
| Storage | Disk 96% penuh, sisa 11 GB | HIGH |
| Disk | 5 dir `checkpoints_aug*` sisa eksperimen | LOW |
| Android | Scaffold belum ada | (planned) |
| Package | `pip install gemahutan-ml` belum dibikin | (planned) |

## 1. Model (Audit utama)

### Sumber kebenaran
- `ml/reports/eval.md`, `ml/reports/metrics.json`, `ml/reports/field_metrics.json`
- `/api/v1/model/info` runtime.
- Manifest audio: `ml/data/manifest.csv`.

### Angka
- Test akurasi: **0.7156** (1370 klip, 25 spesies + 1 negatif).
- Val akurasi: **0.6528**.
- Macro F1: **0.7194**.
- 1 spesies dengan support <8: **Prinia familiaris** (support=3).
- 4 spesies dengan precision-recall gap > 0.3:
  - Prinia familiaris: P=0.333 R=1.000 (recall penuh, precision rendah, support kecil)
  - Cinnyris jugularis: P=0.500 R=0.875
  - Passer montanus: P=0.800 R=0.500
  - `_negative` P=0.786 R=0.478
- 6 spesies AUC-PR < 0.6: Hirundo tahitica 0.352, Gallus gallus 0.421, Aplonis panayensis 0.513, Prinia familiaris 0.533, Dicrurus macrocercus 0.572, Anthreptes malacensis 0.578.

### Tangga degradasi (`field_metrics.json`)
| Kondisi | Akurasi |
|---|---|
| kontrol reencode | 0.6759 |
| bersih tanpa ND | 0.7034 |
| bersih (semua) | 0.7156 |
| angin | 0.6250 |
| hujan ringan | 0.6065 |
| kota | 0.5880 |
| jarak 30 m | 0.5622 |
| hujan deras | 0.5370 |
| jarak 100 m | 0.5194 |
| gabungan berat | 0.2817 |

Korpus lapangan nyata (ril): Xeno-canto kotor 0.6594, ponsel iNaturalist 0.5082, pengecoh 0.6172 (tinggi = perlu diperbaiki).

### Bug lisensi yang aktif (SERIUS)

`ml/data/manifest.csv` masih memuat 446 klip ND dari 1370 (32.6%).
`ml/data/prepare.py` tidak menyaring ND sebelum membuat splits.
Akibat terukur:
- train: 304 klip ND
- val: 69 klip ND
- test: 73 klip ND

Artinya model Track B dilatih, divalidasi, dan diuji dengan data yang lisensinya melarang turunan. Pipeline worker memotong audio = pelanggaran ND aktif.

Simulasi: kalau ND dibuang, dataset tinggal 924 klip, semua 26 spesies masih >= 5 klip. Aman.

### Celah model lain

1. **Confidence tidak dikalibrasi** sebagai probabilitas. Yang dikalibrasi hanya threshold per spesies (prediksi keputusan ya/tidak), bukan nilai `confidence` itu sendiri. README menyebut "confidence terkalibrasi" - itu klaim menyesatkan, perlu dikoreksi.
2. **Threshold `_negative` (0.15) terlalu rendah** sehingga 61.7% jendela pengecoh lolos deteksi di atas ambang.
3. **Tangga degradasi bukan audio lapangan** - simulasi ffmpeg. Angka `0.5194 pada jarak 100 m` adalah simulasi, bukan realita lapangan. Jangan diklaim sebagai kemampuan lapangan.
4. **Augmentasi memperburuk** (eksperimen terdokumentasi di `field_experiments.md`): latih dari nol dengan augmentasi turunkan akurasi bersih ke 0.5862.
5. **Latency CPU 3.4x realtime** (5.75 detik audio diproses 19.4 detik) belum diukur di HP/AudioMoth.

### Saran konkret

1. **Saring ND dari manifest + splits + embeddings** sebelum apa pun:
   ```bash
   python3 -c "
   import csv, json
   keep=[]
   with open('ml/data/manifest.csv') as f:
       for row in csv.DictReader(f):
           if 'nd' in (row.get('license') or '').lower(): continue
           keep.append(row)
   # tulis ulang manifest dan regenerate splits.json
   "
   ```
   Lalu `python ml/data/prepare.py`, `python ml/data/extract_embeddings.py`, `python ml/train.py --epochs 300 --hidden 256 --lr 0.001 --seed 42 --resume`. Target: akurasi uji turun sedikit (estimasi 0.66 - 0.70) tapi data bersih secara lisensi.

2. **Perkuat Prinia familiaris** dari 3 ke minimal 8 klip. Tambah 5 - 10 rekaman Xeno-canto lisensi non-ND/NC. Atau turunkan threshold (sekarang 0.6) dan akui model lemah untuk spesies ini.

3. **Kalibrasi confidence** dengan temperature scaling: jalankan prediksi di test set, hitung NLL sebelum, fit temperature T pada val set, terapkan ke confidence. Update `ml/engines/embedding_clf.py` agar confidence = softmax(logit / T).

4. **Naikkan threshold `_negative`** dari 0.15 ke 0.30 atau 0.35 untuk压制 61.7% deteksi palsu pengecoh. Ukur dampak pada recall spesies target.

5. **Laporan per spesies**, bukan akurasi global. Support 3 - 8 klip artinya satu klip menggeser 12 poin. Klaim harus menyebut support.

6. **Jangan tulis ulang README dengan angka baru sampai ada validasi ulang** di db bersih + data lapangan sendiri (30 - 50 menit).

## 2. API & Authorization

### Probe runtime
- Endpoint: 36 path (26 GET, 10 POST, 4 PATCH, 4 DELETE).
- `verify_features.py`: **26/28 PASS**.
- `security_check.py`: **6/6 PASS**.
- Test API 57, worker 25, web 57 (database bersih).

### Celah yang ditemukan saat probe

| Endpoint | Admin | Ranger | Status |
|---|---|---|---|
| `/api/v1/recordings/{id}` | 200 | 404 | OK (filter `uploaded_by`) |
| `/api/v1/recordings/{id}/detections` | 200 | 404 | OK |
| `/api/v1/recordings/{id}/audio` | 200 | 404 | OK |
| `/api/v1/users` | 200 | 403 | OK (admin only) |
| `/api/v1/jobs?limit=5` | 200 | **200** | LEAK |
| `/api/v1/batches` | 200 | **200** | LEAK |
| `/api/v1/sites` | 200 | 200 | OK by design (shared) |
| `/api/v1/devices` | 200 | 200 | OK by design (shared) |
| `/api/v1/stats/overview` | 200 | **200** | LEAK |
| `/api/v1/stats/species` | 200 | **200** | LEAK |
| `/api/v1/exports/verified?format=csv` | 200 | **200** | LEAK |
| `/api/v1/exports/recordings?format=csv` | 200 | **200** | LEAK |

### Keputusan produk yang dibutuhkan

`jobs`, `batches`, `stats`, `exports` tidak memfilter ownership.
Untuk lomba USB 2026 dengan satu kawasan (single-tenant), ini bisa
diterima. Untuk aplikasi multi-kawasan, ini blocker keamanan.

**Saran**: jika single-tenant (keputusan saat ini), tambahkan komentar eksplisit di `docs/DECISIONS.md` dan kunci dengan audit log. Jika multi-tenant (masa depan), tambahkan `where uploaded_by = current_user.id or role='admin'` di setiap query. Sumber kode: `apps/api/app/routers/jobs_stream.py`, `batches.py`, `exports.py`, `model.py` untuk `stats`.

### Celah lain
- Tidak ada `audit_log` untuk perubahan peran, verifikasi, atau retry. Sulit forensik kalau ada masalah.
- `magic bytes` audio belum divalidasi - hanya ekstensi dan MIME. File teks bernama `.wav` bisa lolos validasi ringan (sudah ada validator ffprobe, bagus).
- MFA admin belum, refresh token rotation sudah (dari commit terbaru).
- Rate limit hanya di login, tidak di endpoint berat (`/spectrogram`, `/audio`).

## 3. Worker Reliability

### Bug aktif dari log (1 jam terakhir)

1. **FK violation `acoustic_indices`**: rekaman 342 gagal, lalu UPDATE berikutnya juga gagal karena transaksi aborted. Pola:
   ```
   ForeignKeyViolation: acoustic_indices.recording_id -> recordings
   InFailedSqlTransaction: commands ignored until end of transaction block
   ```
   Akar: insert acoustic_indices sebelum recording di-commit di sesi yang sama, atau session rollback tidak dilakukan setelah error.

2. **`noverlap must be less than nperseg`** scipy error pada audio sangat pendek. Frekuensi: 2 dari 5 job gagal.

3. **webm corrupt** dari rekaman peramban terputus: 2 dari 5 gagal.

5/29 jobs gagal total (17%).

### Celah reliability lain
- Tidak ada DLQ (dead letter queue) terpisah; job yang gagal permanen menumpuk di tabel jobs tanpa cleanup otomatis.
- Retry counter `attempts=3` lalu `failed`. Tidak ada inspeksi terpusat untuk admin.
- `worker.py` pakai session SQLAlchemy sinkron; ada risiko deadlock saat load tinggi.
- Heartbeat ke Redis ada, tapi tidak ada metrik age alert ke operator.

### Saran konkret

1. **Fix FK + transaction**: bungkus setiap insert detection/indices/recording dalam `try/except` lalu `session.rollback()`. Atau pakai `session.begin_nested()`.
   ```python
   try:
       session.add(recording)
       session.flush()  # dapat id
       session.add(acoustic_indices)
       session.commit()
   except IntegrityError:
       session.rollback()
       raise
   ```

2. **Guard `noverlap >= nperseg`**: di `worker.py:415`, pastikan `noverlap = min(nperseg // 2, max(1, nperseg - 1))`.

3. **DLQ view**: tambah endpoint `/api/v1/jobs?status=failed` plus tombol "Retry" (sudah ada di CONTRACT_v2), dan tampilkan di dashboard admin.

4. **Webm validation**: tolak webm < 1 KB di API (sudah ada validator ffprobe, tinggal tambah panjang minimum).

## 4. Web (BLOCKER)

### Temuan
- `apps/web/` folder source: **dihapus semua** dari worktree (`D apps/web/...` 47 file belum commit).
- `docker-compose.yml` **tidak ada service `web`**.
- Image `gemahutan-web` **tidak ada** di `docker images`.
- `curl http://localhost:3001` timeout.
- `verify_features.py` PWA gagal 2/2 (manifest + service worker).
- Landing + dasbor tidak bisa diuji.

### Saran konkret

1. **Rebuild web dari nol** (sesuai `docs/USERFLOW_WEB.md`). Stack: Next.js 15 + TS + Tailwind dark + shadcn/ui (sesuai `DESIGN.md`).
2. **Tambah service `web` di docker-compose.yml**:
   ```yaml
   web:
     build:
       context: .
       dockerfile: apps/web/Dockerfile
     ports: ["127.0.0.1:3001:3000"]
     env_file: .env
     depends_on:
       api: {condition: service_healthy}
   ```
3. **PWA beneran**: manifest valid, service worker tidak cache API (cuma aset statis), install prompt muncul.
4. **Lighthouse mobile target 90+** di 390 px. Tap target 44 px. Fokus keyboard terlihat.

## 5. Android (Planned)

### Status
- Nol kode di repo. Folder `apps/android` tidak ada.
- Kontrak data dari `CONTRACT_v2.md` sudah jelas.
- Izin yang dibutuhkan: `RECORD_AUDIO`, `ACCESS_FINE_LOCATION`, `FOREGROUND_SERVICE_MICROPHONE`, `POST_NOTIFICATIONS`.

### Saran konkret

1. **Scaffold Kotlin** (bukan Flutter kecuali target iOS):
   ```bash
   mkdir -p apps/android
   cd apps/android
   # gradle init, set minSdk 26, targetSdk 34, applicationId id.gemahutan.app
   ```
2. **Modul**: `capture` (MediaRecorder), `queue` (Room SQLite), `sync` (Retrofit + OkHttp), `ui` (Compose Material3 dark).
3. **End-to-end test**: rekam 30 menit di emulator, matikan proses, hidupkan, pastikan antrean pulih.

## 6. Package Python (Planned)

### Status
- Belum ada `setup.py` atau `pyproject.toml` di root.
- `ml/` masih script-driven, bukan library.

### Saran konkret

1. **Bikin `pyproject.toml`** dengan entry point:
   ```toml
   [project.scripts]
   gemahutan-train = "gemahutan.ml.train:main"
   gemahutan-eval = "gemahutan.ml.evaluate:main"
   gemahutan-degrade = "ml.degradation:main"
   ```
2. **Build wheel** lewat `python -m build`, publish ke PyPI atau GitHub Releases.
3. **Dependensi**: numpy, librosa, scikit-maad, birdnetlib, resampy (wajib), soundfile, scipy.

## 7. Storage & Deployment

### Temuan
- Disk 96% penuh, sisa 11 GB.
- `ml/data/degraded` 12 GB (tangga degradasi).
- `ml/data/audio` 7.6 GB.
- 5 dir `checkpoints_aug*` dari eksperimen augmentasi.

### Saran konkret

1. **Hapus `checkpoints_aug60/`, `checkpoints_aug120/`, `checkpoints_aug180/`, `checkpoints_augft/`** kecuali masih dipakai. Simpan hanya `checkpoints/` (produksi) + `checkpoints_aug/` (eksperimen final).
2. **Pindah `ml/data/degraded` ke disk lain** atau `.dockerignore` ketat (sudah ada, pastikan).
3. **Backup policy**: script `ops/backup.sh` ada, tapi belum diuji restore object storage.

### Deployment readiness

| Butir | Status |
|---|---|
| Password demo | Default `admin123` di seed.py - HARUS diganti sebelum publik |
| `ALLOW_REGISTRATION` | Default true - HARUS false sebelum publik |
| CORS | Hardcoded localhost - HARUS domain publik |
| `SECRET_KEY`, `JWT_SECRET` | ENV var, harus random 32 bytes |
| HTTPS | Caddy di `deploy/Caddyfile`, otomatis Let's Encrypt |
| HSTS, CSP, security headers | BELUM dicek di Caddyfile |
| MFA admin | BELUM |
| `pip-audit`, `npm audit` di CI | BELUM |

## 8. Yang BUKAN temuan (sudah benar)

- `/healthz` 200, `/readyz` 200, semua service healthy.
- Owner check di recordings, detections, sites sudah benar.
- Cascade engine BirdNET + embedding classifier, threshold per-spesies, MergeBirdNETB - Track B.
- Localization azimuth gcc-phat dengan array lines resolved (arah kembar dipisah).
- Worker tulis progress 0 - 100 per tahap (sesuai CONTRACT_v2).
- Token revocation di Redis jalan.
- Login rate limit 5 per menit.
- FFprobe validasi audio sebelum unggah.
- BirdNET-Analyzer v2.4, 6522 spesies.
- 25 spesies Indonesia dengan ambang kalibrasi.

## 9. Prioritas eksekusi (lomba USB)

| # | Tugas | Bloker | Effort |
|---|---|---|---|
| 1 | Saring ND dari manifest + splits + embeddings | Lisensi | 4 jam |
| 2 | Fix FK + transaction abort di worker | Reliability | 2 jam |
| 3 | Guard `noverlap >= nperseg` | Reliability | 30 menit |
| 4 | Rebuild web dasbor (15 layar dari USERFLOW_WEB) | Lomba | 3 minggu |
| 5 | Ganti password admin demo + `ALLOW_REGISTRATION=false` | Publik | 15 menit |
| 6 | Tambah service web ke docker-compose.yml + Dockerfile | Lomba | 1 jam |
| 7 | Hapus `checkpoints_aug*` eksperimen, sisa 11 GB aman | Disk | 15 menit |
| 8 | Lock keputusan single-tenant di `DECISIONS.md` | Authorization | 30 menit |
| 9 | Audit log untuk perubahan peran, verifikasi | Forensik | 1 hari |
| 10 | Scaffold Android Kotlin | Capture lapangan | 2 minggu |

Saran nomor 1, 2, 3, 5, 7 selesai dalam satu hari kerja. Setelah
itu rebuild web dan lomba aman.
