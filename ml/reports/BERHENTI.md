# BERHENTI: status Lampiran 4 (putaran streaming + korpus v5)

Ditulis 29 Sep 2026 setelah commit terakhir. Keluaran audit disalin dari
`ops/audit_model.py`.

## Keluaran audit model

```
audit_model.py v2 sha256 2b9f0e7727889cb2
[LULUS  ] C01 ruff bersih                                          All checks passed!
[LULUS  ] C02 pytest ml/tests                                      16 passed
[LULUS  ] C03 test worker (container)                              33 passed
[LULUS  ] C04 test API (container)                                 99 passed, 3 skipped
[LULUS  ] C05 checkpoint cocok MANIFEST                            ff01eb96e002
[LULUS  ] C06 thresholds.json terbaca                              26 kunci, median 0.300, nol 0
[LULUS  ] C07 fixture snapshot == mesin produksi                   selisih 0.0000, label beda 0/10
[LULUS  ] C08 tidak ada pemilihan memakai label
[LULUS  ] C09 uji independen produksi                              acc 0.7557, F1 0.6861, n=131
[LULUS  ] C10 CV bersarang valid                                   F1 0.7288 [0.680, 0.757]
[LULUS  ] C11 e2e lengkap dan konsisten                            448 dievaluasi, 3 gagal, P 0.677 R 0.729
[LULUS  ] C12 worker memakai checkpoint repo                       ff01eb96e002
[MELESET] C13 open-set: FP pengecoh <= 0,15 & recall >= 0,70       FP 0.526 (n=38), recall 0.704 (n=247)
[MELESET] C14 mutu classifier: F1 CV >= 0,78, independen F1 >= 0,75  F1 CV 0.729 [0.680], independen 0.686
[MELESET] C15 ponsel iNat e2e: P >= 0,75 & R >= 0,62               P 0.659 R 0.527 (n=55)
[LULUS  ] C16 latensi 60 menit < 900 dtk, RSS < 1800 MB            94.6 dtk, RSS 1134 MB
[GAGAL  ] C17 lisensi tiap klip latih produksi sah                 8229 klip latih, lisensi terlarang 3205
[GAGAL  ] C18 label lemah ditangani (bukan 3 detik pertama)        metode energi, produksi masih v3
[LULUS  ] C19 promosi model lewat gerbang                          produksi masih LR v3 asli
[LULUS  ] C20 satu sumber angka, tidak ada angka usang
[MANUSIA] C21 data lapangan asli >= 30 menit                       baru 2.1 menit
[LULUS  ] C22 reproduksi satu perintah

16 LULUS, 2 GAGAL, 3 MELESET, 1 MANUSIA
Butir rubrik yang lulus penuh: [1, 2, 3, 4, 7, 9] -> 6/10
```

sha256 kedua audit dicek awal dan akhir putaran: `audit_model.py`
2b9f0e7727889cb25f81082f45fcd65a42ed2aef680f09ffbc0148e27084bd2d (tidak
berubah).

## Yang selesai putaran ini

**Butir 7 (RAM / siap operasi) -> LULUS.** Streaming audio per jendela
(`ml/engines/streaming.py`), BirdNET dan Track B tidak lagi memuat audio penuh.
Rekaman 60 menit: RSS 3,9 GB -> 1,1 GB, 94,6 detik, 38x realtime. Paritas
44/44 deteksi identik dengan mesin lama. `latensi.json` ditulis sesuai skema
ML_00 (`identik_8_demo: true`).

**Butir 8 (lisensi) -> diaudit dengan bukti.** 3.205 klip iNat tidak punya
observation_id di dataset sumber (skema parquet dicek), iNat API tidak menerima
UUID lookup. Korpus v5 dibangun dengan negatif XC berlisensi terbukti.

**Butir 6 (deteksi palsu) -> progres, belum lulus.** Sapuan cascade 3 putaran.
Konfirmasi BirdNET (`trackb_wajib_birdnet`) menaikkan presisi 0,64 -> 0,80 dan
menurunkan deteksi palsu 44% -> 20%, tetapi recall target turun di bawah syarat.
Konfigurasi terbaik `kuat06` (ambang_kuat 0,6). Belum ada yang menembus target
(FP <= 0,15, P >= 0,75, R >= 0,62).

## Kandidat v5 (negatif iNat -> negatif XC): TIDAK lulus gerbang

- Korpus: v3 8.356 -> v5 6.633 klip (train 6.379, val 127, uji 127; val/uji tidak berubah).
- Negatif XC: 1.482 klip / 237 spesies (target 300 spesies tidak tercapai).
- Akurasi split uji (pool sama, normalisasi masing-masing): v3 0,7795, v5 0,7638 (-0,0157).
- CV bersarang v5 (pool v5): F1 0,6939 [0,6446, 0,7229].
- 3 spesies turun recall > 0,15, masing-masing 1 klip (support 5-6), di dalam derau.
- Kesimpulan: produksi tetap LR v3. Detail di `ml/reports/hasil_negatif.md`.

## Sisa pekerjaan

1. **C17 (lisensi)**: butuh keputusan manusia. Korpus v5 lisensi-bersih tapi
   mutunya tidak menang. Pilihan: promosikan v5 (lulus lisensi, sedikit turun
   mutu) atau pertahankan v3 (mutu, lisensi belum terbukti).
2. **C18 (label 3 detik pertama)**: `ml/extract_jendela_bersuara.py` siap,
   belum dijalankan penuh (8.259 klip, ~4 jam). Kandidat terpisah dari v5.
3. **C13**: skor energi (`pakai_energi`), kombinasi terbaik setelah gerbang.
4. **C14**: data spesies lemah, pooling beberapa jendela, MLP kecil.
5. **C15**: kebijakan open-set di ponsel, analisis kesalahan iNat.
6. **C21 (data lapangan)**: butuh rekaman tim >= 30 menit.
7. **Negatif non-burung**: gagal (XC throttle setelah unduhan massal, kandidat
   sedikit). Dicatat di `hasil_negatif.md`.

## Disk

Sisa ~8 GB. Audio negatif XC 2,49 GB di `ml/data/negatif_xc/` (gitignored,
dibangun ulang dari manifest). Tidak ada unduhan baru tanpa izin.

## Berkas baru putaran ini

- `ml/engines/streaming.py`, `ml/engines/birdnet.py` (rewrite), `ml/engines/embedding_clf.py`
- `ml/cek_lisensi_inat.py`, `ml/unduh_negatif_xc.py`, `ml/unduh_negatif_nonburung.py`
- `ml/siapkan_korpus_v5.py`, `ml/bandingkan_v5.py`, `ml/jalankan_v5_pipeline.sh`
- `ml/sapu_cascade.py`, `ml/sapu_cascade2.py`, `ml/sapu_cascade_v3.py`, `ml/hitung_lapor.py`
- `ml/extract_jendela_bersuara.py`, `ml/tests/test_v5_dryrun.py`
- `ml/reports/`: audit_lisensi.md, benchmark_ram.md, data_tambahan.md,
  hasil_negatif.md, sapu_cascade*.md/json, lapor_baseline_vs_terpilih.md/json,
  bandingkan_v5.md/json, eval_bersarang_v5.json, oof_bersarang_v5.npz, v5_pipeline.log