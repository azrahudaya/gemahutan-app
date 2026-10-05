# Manual GemaHutan

Cara memakai aplikasi petugas GemaHutan per peran. Halaman publik `/dokumentasi` hanya
membahas "Coba contoh" di halaman depan. Ruang lingkup dan keputusan produk ada di
`docs/VISI_DAN_RUANG_LINGKUP.md`.

> **Keadaan 3 Oktober 2026.** Aplikasi petugas masih dikunci `apps/web/src/middleware.ts`
> di gemahutan.site. Manual ini menjelaskan aplikasi yang akan dibuka. Bagian yang ditandai
> **(target)** belum dibuat.

Isi manual ini ditulis dari keadaan aplikasi dan hasil pengukuran yang sudah ada,
bukan dari rencana. Semua angka batas bisa diperiksa ulang di `ml/reports/` dan
lewat `GET /api/v1/model/info`.

## 1. Prasyarat

- Peramban terbaru: Chrome, Edge, atau Firefox. Peramban lama tanpa MediaRecorder
  hanya bisa mengunggah berkas, tidak bisa merekam dari mikrofon.
- Akun aktif dari admin kawasan. Tidak ada pendaftaran mandiri di produksi
  (`ALLOW_REGISTRATION=false`). Di lingkungan pengembangan pendaftaran masih terbuka.
- Berkas audio berformat wav, mp3, flac, ogg, m4a, aac, opus, atau webm.
  Sekali unggah maksimal 20 berkas.
- Minimal satu lokasi pemantauan. Unggahan tanpa lokasi ditolak, karena rekaman
  harus punya titik perekaman.
- Jaringan ke alamat API. Peta memakai ubin OpenStreetMap, jadi tanpa jaringan
  peta kosong, tetapi daftar lokasi dan koordinatnya tetap tampil.

## 2. Masuk dan peran pengguna

Masuk lewat halaman `/login` dengan email dan kata sandi. Akun dibuat admin kawasan.
**(target)** Admin menambah akun dari aplikasi, petugas menerima email undangan untuk
membuat sandi. Saat ini akun dibuat lewat perintah di server. Lupa sandi: tautan atur
ulang dikirim ke email, setelah SMTP diisi di server.

Di lingkungan pengembangan ada akun contoh `admin@gemahutan.id`. Server produksi tidak
punya akun contoh maupun data demo.

| Peran | Boleh melakukan | Tidak boleh |
|---|---|---|
| `ranger` | Rekam dari peramban, unggah, melihat hasil rekamannya sendiri (pemutar, spektrogram, deteksi), simulasi perkiraan lokasi **(target)** | Melihat rekaman orang lain, dashboard kawasan, ekspor, halaman Model dan Perangkat, verifikasi, mengelola data acuan |
| `researcher` (peneliti) | Melihat semua rekaman, verifikasi, ekspor, dashboard, peta, laporan, halaman Model dan Perangkat, mengulang job | Mengelola akun, lokasi, perangkat, spesies prioritas |
| `admin` | Semua, termasuk akun, lokasi, perangkat, dan spesies prioritas **(target)** | - |

Ranger sudah dibatasi ke rekamannya sendiri di API. Pembatasan ekspor, dashboard, dan
halaman Model/Perangkat untuk ranger masih **(target)**.

Kontrol yang pasti ditolak API tidak ditampilkan di antarmuka. Tombol tambah lokasi
dan perangkat hanya muncul untuk admin, tombol verifikasi hanya untuk peneliti dan
admin.

## 3. Daftar halaman

| Halaman | Isi |
|---|---|
| `/dashboard` | Angka ringkas, rekaman terbaru, status worker |
| `/recordings` | Daftar rekaman dengan filter lokasi, spesies, keyakinan, status, dan tanggal |
| `/recordings/{id}` | Detail rekaman: pemutar audio, spektrogram, daftar deteksi, tombol verifikasi, status job |
| `/upload` | Unggah berkas tunggal dan unggah batch sampai 20 berkas |
| `/rekam` | Rekam langsung dari mikrofon peramban |
| `/species` | Daftar spesies dengan ambang keputusan dan jumlah deteksi |
| `/sites` | Peta lokasi, arah datang dan perkiraan jangkauan, daftar lokasi |
| `/sites/{id}` | Detail lokasi, peta, rekaman terakhir, koreksi data untuk admin |
| `/devices` | Perangkat perekam: jenis, jumlah kanal, jarak antar mikrofon, jumlah rekaman |
| `/model` | Dua jalur deteksi, ambang, dan batas yang sudah diukur |
| `/laporan` | Ringkasan siap cetak dengan angka yang dibaca dari API |
| `/admin/users` | Daftar akun, ubah peran, hapus akun. Hanya admin. Tambah akun lewat undangan **(target)** |
| `/dokumentasi` | Dokumentasi publik untuk "Coba contoh" |

Halaman **(target)** yang belum ada: pengaturan spesies prioritas,
laporan bulanan per kawasan (menggantikan ringkasan `/laporan` sekarang).

## 3a. Fitur Tahap 1 yang belum dibuat (target)

- **Spesies prioritas.** Ditandai otomatis dari IUCN CR/EN/VU dan Permen LHK P.106/2018,
  admin bisa menambah. Lokasi tepatnya hanya terlihat admin dan peneliti.
- **Peringatan email** ke admin dan peneliti saat spesies prioritas terdeteksi.
- **Simulasi perkiraan lokasi.** Tersedia di `/simulasi`. Pengguna menaruh 2 sampai 4
  alat virtual di peta, memilih derau dan sinkronisasi jam, lalu sistem menunjukkan
  arah tiap alat dan area perkiraan asal suara dari arah dan jarak.
- **Laporan bulanan per kawasan**, siap cetak.
- **Penyimpanan audio.** Audio penuh 90 hari, lalu hanya potongan di sekitar deteksi.

## 4. Unggah berkas dan unggah batch

Semua unggahan lewat `/upload`, dan keduanya masuk ke pipeline yang sama sehingga
hasil deteksinya identik.

1. Pilih lokasi perekaman. Pilihan ini wajib. Perangkat perekam opsional, tetapi
   mengisinya membuat jumlah rekaman per perangkat bisa dihitung.
2. Pilih satu sampai dua puluh berkas audio.
3. Kirim. Bilah progres menunjukkan persentase unggahan berkas, bukan persentase
   analisis. Analisis berjalan setelah berkas selesai diunggah.
4. Hasil per berkas ditampilkan: nama berkas, status, nomor rekaman, dan pesan galat
   kalau ada. Satu berkas gagal tidak membatalkan berkas lain.
5. Pantau pemrosesan lewat bagian batch terbaru (jumlah selesai, gagal, dan progres
   rata-rata) atau dengan membuka rekaman untuk melihat tahap yang sedang berjalan.

Setiap unggahan batch diberi satu nomor batch. Kumpulan batch terbaru ditampilkan
di halaman yang sama, urut terbaru dulu.

## 5. Rekam dari peramban

1. Buka `/rekam`. Peramban meminta izin mikrofon, dan izin itu wajib diberikan.
2. Pilih lokasi perekaman sebelum mulai.
3. Tekan tombol mulai, biarkan berjalan selama yang dibutuhkan, lalu hentikan.
4. Hasil rekaman diunggah sebagai `audio/webm` dengan sandi Opus (128 kbps) dan
   langsung masuk antrean pemrosesan.

Peramban tanpa dukungan MediaRecorder webm menampilkan pesan bahwa perekaman tidak
bisa dilakukan. Rekaman peramban adalah berkas satu kanal, jadi arah datang tidak
bisa dihitung darinya (lihat bagian 10).

## 6. Memverifikasi deteksi

Buka satu rekaman, lalu pilih deteksi yang ingin diperiksa. Tersedia tiga pilihan:
Benar, Salah, dan Ragu. Verifikasi disimpan per deteksi beserta waktu dan nama
pemeriksanya.

- Hanya peneliti dan admin yang bisa menyimpan verifikasi.
- Hasil verifikasi bukan sekadar label. Deteksi yang ditandai Benar bisa dijadikan
  bahan latih ulang classifier lewat prosedur di `README.md`, atau diunduh lewat
  `/api/v1/exports/verified`.
- Angka keyakinan adalah skor model, bukan peluang benar. Verifikasi manusialah yang
  menentukan, terutama untuk deteksi spesies langka.

## 7. Membaca ambang per spesies

Ambang adalah skor minimum supaya satu kandidat dilaporkan sebagai deteksi. Ambang
disetel per spesies karena model jauh lebih yakin pada jenis yang sering muncul di
data latih.

- Ambang rendah (0,10 sampai 0,20) berarti lebih banyak yang dilaporkan, dengan
  risiko deteksi palsu lebih tinggi.
- Ambang tinggi (0,50 sampai 0,60) berarti hanya kandidat yang sangat yakin yang
  muncul, dengan risiko kejadian nyata terlewat.
- Angka yang dipakai pipeline berasal dari kalibrasi di `ml/reports/thresholds.json`,
  lalu disalin ke basis data (`make sync-thresholds`). `seed.py` membaca berkas yang
  sama, supaya angka di halaman Spesies tidak melenceng setiap kali seed dijalankan.
- Kandidat di luar daftar model memakai satu nilai penjaga (`_negative`, 0,15),
  supaya kandidat asing tidak otomatis lolos.

Ambang 25 spesies yang dikenal classifier lokal:

| Nama ilmiah | Nama Indonesia | Ambang |
|---|---|---|
| Aegithina tiphia | Cipoh Kacat | 0,25 |
| Amaurornis phoenicurus | Kareo Padi | 0,35 |
| Anthreptes malacensis | Burung Madu Kelapa | 0,10 |
| Aplonis panayensis | Perling Kumbang | 0,30 |
| Arachnothera longirostra | Pijantung Kecil | 0,30 |
| Centropus bengalensis | Bubut Alang-alang | 0,35 |
| Chalcophaps indica | Delimukan Zamrud | 0,20 |
| Cinnyris jugularis | Burung Madu Sriganti | 0,15 |
| Cisticola juncidis | Cici Padi | 0,20 |
| Corvus macrorhynchos | Gagak Kampung | 0,15 |
| Dicrurus macrocercus | Srigunting Hitam | 0,20 |
| Gallus gallus | Ayam Hutan Merah | 0,20 |
| Geopelia striata | Perkutut Jawa | 0,40 |
| Haliastur indus | Elang Bondol | 0,25 |
| Hirundo tahitica | Layang-layang Batu | 0,25 |
| Lonchura punctulata | Bondol Peking | 0,20 |
| Merops philippinus | Kirik-kirik Laut | 0,15 |
| Orthotomus sutorius | Cinenen Pisang | 0,20 |
| Passer montanus | Burung Gereja Erasia | 0,20 |
| Prinia familiaris | Perenjak Jawa | 0,60 |
| Pycnonotus aurigaster | Kutilang | 0,15 |
| Pycnonotus goiavier | Merbah Cerukcuk | 0,30 |
| Rhipidura javanica | Kipasan Belang | 0,25 |
| Spilopelia chinensis | Tekukur Biasa | 0,15 |
| Todiramphus chloris | Cekakak Sungai | 0,15 |

## 8. Arti tiap tahap job

Satu rekaman diproses sebagai satu job. Progres ditulis setelah setiap tahap selesai,
jadi angkanya bergerak bertahap.

| Tahap | Progres | Yang terjadi |
|---|---|---|
| `antre` | 0 | Job masuk antrean Redis dan belum diambil worker |
| `unduh` | 10 | Worker mengambil berkas audio dari penyimpanan objek |
| `dekode` | 20 | Audio dibaca, disamakan menjadi satu kanal 48 kHz |
| `birdnet` | 30 sampai 60 | BirdNET menandai kandidat burung per potongan 3 detik |
| `klasifikasi` | 60 sampai 75 | Classifier 25 spesies memberi skor akhir, ambang per spesies dipakai |
| `lokalisasi` | 80 | Arah datang dan perkiraan jarak dihitung kalau geometri perangkat mendukung |
| `indeks` | 88 | Indeks soundscape ACI, NDSI, ADI, BI dihitung |
| `spektrogram` | 96 | Gambar spektrogram dibuat dan disimpan |
| `selesai` | 100 | Semua hasil tersimpan di basis data |
| `gagal` | tetap di angka terakhir | Satu tahap gagal, job berhenti, tahap berikutnya tidak dijalankan |

Kalau satu tahap gagal, progres tidak dikembalikan ke nol supaya terlihat sejauh mana
prosesnya sudah berjalan. Job bisa diulang dari halaman rekaman, dan percobaan otomatis
dibatasi tiga kali. Job yang gagal ikut muncul di daftar job aktif.

## 9. Ekspor data

Ada dua keluaran, keduanya berformat csv secara bawaan dan json kalau diminta.

| Keluaran | Isi | Parameter |
|---|---|---|
| `/api/v1/exports/verified` | Deteksi terverifikasi: nomor deteksi, rekaman, lokasi, waktu, spesies, keyakinan, mesin, status verifikasi, waktu verifikasi | `status` (correct, incorrect, uncertain, all), `site`, `format` |
| `/api/v1/exports/recordings` | Daftar rekaman dengan jumlah deteksi dan jumlah yang sudah diverifikasi | `site`, `format` |

Semua ekspor butuh token. Dari terminal, sertakan header
`Authorization: Bearer <access_token>`.

## 10. Batas yang sudah diukur

Angka-angka ini berasal dari pengukuran, bukan perkiraan, dan tersedia juga lewat
`GET /api/v1/model/info` pada blok `limits`.

- Model lokal mengenal 25 spesies, kira-kira 1,4 persen dari sekitar 1.800 spesies
  burung Indonesia.
- Akurasi pada rekaman ponsel lapangan turun ke **0,5082**, dari 0,7034 pada audio
  bersih tanpa klip ND.
- Pada kelompok pengecoh di luar daftar model, **0,6172** atau 61,7 persen jendela
  masih memicu deteksi di atas ambang. Angka ini yang perlu diturunkan dengan
  verifikasi ahli.
- Korpus lapangan Xeno-canto yang kotor berada di 0,6594.
- Angka audio bersih berasal dari klip Xeno-canto yang tidak pernah didengar di
  lapangan, jadi angka itu batas atas, bukan perkiraan lapangan.
- Skenario hujan, angin, kota, dan jarak pada `ml/reports/field_eval.md` adalah
  simulasi ffmpeg, bukan rekaman lapangan.
- Percobaan menambah data simulasi ke latih tidak menaikkan performa lapangan,
  rinciannya di `ml/reports/field_experiments.md`.

Batas lokalisasi, dari blok `localization` di `/api/v1/model/info`:

- Satu mikrofon tidak bisa menentukan arah sama sekali. Yang bisa ditampilkan hanya
  lingkaran perkiraan jangkauan deteksi.
- Arah butuh minimal dua kanal yang tersinkron. Pada rekaman buatan, galat mediannya
  0,0 derajat pada SNR 30 sampai 5 dB.
- Jarak dari penyusutan amplitudo sangat sensitif: salah taksir level sumber 6 dB
  sudah menggeser hasil dua kali lipat (10 m terbaca 20 m).
- Triangulasi beberapa perangkat butuh jam yang tersinkron. Tanpa itu selisih waktu
  tiba antar perangkat tidak sah.
- Rekaman buatan yang dipakai menguji belum memuat gema, pantulan, dan kicauan
  bertumpuk seperti subuh di hutan, jadi angka ujinya batas atas mutu.

## 11. Penanganan masalah umum

| Gejala | Sebab | Tindakan |
|---|---|---|
| Berkas ditolak saat diunggah | Ekstensi di luar daftar yang diterima, atau ukuran melebihi batas server | Pakai wav, mp3, flac, ogg, m4a, aac, opus, atau webm |
| Job berstatus gagal | Berkas rusak, audio tidak bisa didekode, atau kegagalan sementara di worker | Buka rekaman, baca pesan galatnya, lalu pakai tombol ulang job. Percobaan otomatis dibatasi tiga kali |
| Spektrogram tidak muncul | Job belum sampai tahap spektrogram | Tunggu tahap selesai, atau periksa status job di halaman rekaman |
| Peta tidak memuat ubin | Jaringan memblokir OpenStreetMap | Daftar lokasi dan koordinat tetap tampil di halaman Lokasi |
| Arah datang tidak muncul di peta | Rekaman mono atau perangkat tanpa jarak antar mikrofon | Hanya perkiraan jangkauan yang bisa ditampilkan. Estimasi arah butuh minimal dua kanal |
| Lokasi tidak bisa dihapus, jawaban 409 | Lokasi masih dipakai rekaman | Pindahkan atau hapus rekaman di lokasi itu lebih dulu |
| Perangkat tidak bisa dihapus, jawaban 409 | Perangkat masih dipakai rekaman | Lepaskan keterkaitan perangkat pada rekaman terkait lewat halaman rekaman |
| Kembali ke halaman masuk sendiri | Sesi berakhir atau token dicabut | Masuk ulang. Access token berlaku 30 menit dan diperbarui lewat refresh token |
| Unggahan batch sebagian gagal | Satu berkas bermasalah tidak membatalkan sisanya | Lihat daftar hasil per berkas, berkas yang gagal memperlihatkan pesannya masing-masing |
| Peran tidak bisa diubah ke ranger sendiri | API menolak mengubah peran diri sendiri (409) | Minta admin lain yang mengubahnya |

## 12. Daftar endpoint API

Semua endpoint butuh token kecuali `/healthz`, `/readyz`, dan tiga endpoint di bawah
`/api/v1/auth`. Tanpa token jawabannya 401.

| Method | Endpoint | Fungsi |
|---|---|---|
| POST | `/api/v1/auth/register` | Buat akun. Tertutup di produksi (`ALLOW_REGISTRATION=false`) |
| POST | `/api/v1/auth/login` | Masuk, hasil access dan refresh token |
| POST | `/api/v1/auth/refresh` | Tukar refresh token jadi access token baru |
| POST | `/api/v1/auth/logout` | Cabut access dan refresh token yang sedang dipakai |
| GET | `/api/v1/me` | Profil dan peran pengguna yang sedang masuk |
| POST | `/api/v1/recordings` | Unggah satu berkas audio |
| POST | `/api/v1/recordings/batch` | Unggah 1 sampai 20 berkas sekaligus |
| GET | `/api/v1/recordings` | Daftar rekaman, ada filter lokasi, perangkat, spesies, keyakinan, status, tanggal |
| GET | `/api/v1/recordings/{id}` | Detail rekaman termasuk progress, stage, dan batch_id |
| PATCH | `/api/v1/recordings/{id}` | Koreksi lokasi, perangkat, atau waktu rekaman |
| DELETE | `/api/v1/recordings/{id}` | Hapus rekaman beserta deteksi, indeks, job, dan audionya |
| GET | `/api/v1/recordings/{id}/detections` | Deteksi per rekaman, termasuk kolom lokalisasi |
| GET | `/api/v1/recordings/{id}/spectrogram` | Gambar spektrogram |
| GET | `/api/v1/recordings/{id}/audio` | Stream audio untuk pemutar |
| GET | `/api/v1/recordings/{id}/indices` | Indeks soundscape ACI, NDSI, ADI, BI |
| GET | `/api/v1/batches` | Daftar batch unggahan beserta progress rata-ratanya |
| GET | `/api/v1/batches/{id}` | Rincian satu batch, status per berkas |
| GET | `/api/v1/jobs` | Status job, filter `status` dan `limit` |
| GET | `/api/v1/jobs/stream` | Siaran status job lewat SSE |
| POST | `/api/v1/jobs/{id}/retry` | Ulangi job yang gagal |
| GET | `/api/v1/species` | Daftar spesies beserta ambang dan jumlah deteksi |
| GET | `/api/v1/species/{id}` | Detail satu spesies |
| GET | `/api/v1/species/{id}/detections` | Riwayat deteksi satu spesies |
| POST | `/api/v1/detections/{id}/verify` | Simpan verifikasi benar, salah, atau ragu |
| GET | `/api/v1/sites` | Daftar lokasi beserta jumlah rekaman dan deteksi |
| POST | `/api/v1/sites` | Tambah lokasi. Hanya admin |
| GET | `/api/v1/sites/{id}` | Detail satu lokasi |
| PATCH | `/api/v1/sites/{id}` | Koreksi lokasi. Hanya admin |
| DELETE | `/api/v1/sites/{id}` | Hapus lokasi. Ditolak 409 kalau masih dipakai rekaman |
| GET | `/api/v1/devices` | Daftar perangkat perekam dan jumlah rekamannya |
| POST | `/api/v1/devices` | Tambah perangkat. Hanya admin |
| PATCH | `/api/v1/devices/{id}` | Ubah perangkat. Hanya admin |
| DELETE | `/api/v1/devices/{id}` | Hapus perangkat. Ditolak 409 kalau masih dipakai rekaman |
| GET | `/api/v1/users` | Daftar akun. Hanya admin |
| PATCH | `/api/v1/users/{id}/role` | Ubah peran. Menolak 409 untuk diri sendiri |
| DELETE | `/api/v1/users/{id}` | Hapus akun. Ditolak 409 kalau masih punya rekaman atau lokasi |
| GET | `/api/v1/stats/overview` | Angka ringkas untuk dashboard dan laporan |
| GET | `/api/v1/stats/species` | Spesies paling sering terdeteksi |
| GET | `/api/v1/stats/timeline` | Jumlah deteksi per hari |
| GET | `/api/v1/model/info` | Mesin yang benar-benar dimuat, ambang, batas, dan cakupan lokalisasi |
| GET | `/api/v1/exports/verified` | Ekspor deteksi terverifikasi, csv atau json |
| GET | `/api/v1/exports/recordings` | Ekspor daftar rekaman dan jumlah deteksinya |
| GET | `/healthz` | Pemeriksaan kesehatan, tanpa token |
| GET | `/readyz` | Kesiapan dependensi, tanpa token |

### Catatan keamanan siaran status

`GET /api/v1/jobs/stream` menerima token lewat parameter query, karena `EventSource`
di peramban tidak bisa mengirim header. Ini pengecualian sadar yang hanya berlaku untuk
endpoint itu. Konsekuensinya URL siaran status jangan dicatat di log akses, jangan
dibagikan, dan jangan disimpan di tempat yang bisa dibaca orang lain. Tanpa token yang
sah, jawabannya tetap 401.

## 13. Cara memeriksa ulang semua ini

```bash
# pemeriksaan fitur lewat HTTP, mencetak PASS atau GAGAL per butir
python3 ops/verify_features.py

# pemeriksaan keamanan stack yang hidup
python3 ops/security_check.py

# ambang di basis data dibandingkan ml/reports/thresholds.json
python3 ops/sync_thresholds.py
```
