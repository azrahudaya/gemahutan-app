# Angka publik GemaHutan

Sumber tunggal angka yang tampil di situs (`/api/v1/model/info`) beserta asalnya.
Peninjau menyamakan proposal dengan berkas ini. Jangan menulis angka langsung di
UI; semuanya lewat `apps/api/app/services/model_status.py`.

## Sumber berkas

| Berkas | Isi |
|---|---|
| `ml/reports/angka_resmi.json` | Angka ringkas untuk `metrics` (CV, independen, e2e). |
| `ml/reports/field_metrics.json` | Angka evaluasi lapangan untuk `limits` (ponsel, pengecoh, bersih). |
| `ml/reports/metrics.json` | Angka evaluasi bersih per split (fallback kalau angka_resmi kosong). |
| `docs/assets/data/e2e_produksi_385147c.json` | Sumber Tabel 6 proposal (presisi/recall per berkas). |

## Angka yang tampil sekarang

### Cakupan model

- Model lokal mengenal 25 spesies target (Track B), kira-kira 1,4 persen dari
  1.834 spesies burung Indonesia (Burung Indonesia, 2026).
- Track A (BirdNET zero-shot) menjaring 6.522 spesies global.

### metrics (dari `angka_resmi.json`)

| Kunci | Nilai | Makna |
|---|---|---|
| f1_cv | 0,729 | F1 makro CV 5-fold |
| f1_cv_ci95 | [0,69; 0,751] | Selang kepercayaan F1 CV |
| acc_independen | 0,756 | Akurasi uji independen |
| f1_independen | 0,607 | F1 uji independen |
| e2e_presisi | 0,677 | Presisi end-to-end |
| e2e_recall | 0,729 | Recall end-to-end |
| fp_pengecoh_berkas | 0,443 | Fraksi berkas pengecoh yang memicu deteksi |

### limits (dari `field_metrics.json`)

| Angka | Nilai | Makna |
|---|---|---|
| inat akurasi top-1 | 0,5213 | Akurasi pada rekaman ponsel iNaturalist |
| bersih_tanpa_nd akurasi top-1 | 0,7559 | Akurasi pada audio bersih (Xeno-canto) |
| other deteksi_palsu | 0,3065 | Fraksi JENDELA pengecoh yang memicu deteksi |

## Perbedaan dengan proposal Tabel 6 (perlu disamakan peninjau)

1. **Pengecoh**: situs menampilkan `deteksi_palsu` per JENDELA (0,3065), proposal
   menulis per BERKAS (46 dari 97 = 47%). Sumber berkas ada di
   `docs/assets/data/e2e_produksi_385147c.json` (`field/other.berkas_dengan_deteksi_target`).
2. **Presisi/recall e2e**: situs `e2e_presisi 0,677` dan `e2e_recall 0,729`, sedangkan
   proposal Tabel 6 menulis presisi 0,751 (dari `uji_independen.presisi` 0,7422 atau
   angka lain) dan recall ponsel 0,613 (dari `field/inat.recall` 0,6126). Perlu satu
   definisi yang dipakai keduanya.

Rekonsiliasi final dilakukan setelah ML_11 (promosi v5) dengan menulis ulang
`ml/reports/angka_resmi.json` dan menyesuaikan `limits` di model_status.py memakai
istilah per berkas.
