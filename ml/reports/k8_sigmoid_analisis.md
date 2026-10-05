# K8 kepala sigmoid: bukan "satu perubahan terhadap produksi"

Diperiksa ke kode sebelum mulai mengerjakan, dan hasilnya mengubah perkiraan
biaya K8. Dicatat di sini supaya keputusannya bisa diaudit.

## Jalur inferensi produksi memaku softmax

- `ml/engines/embedding_clf.py` `_calibrated_probs()` selalu menghitung
  `exp(z)/sum(exp(z))`. Tidak ada cabang sigmoid.
- `ml/resep.py` `ModelLogReg.predict()` juga softmax.
- `grep -rn "sigmoid" ml/engines/ ml/resep.py` kosong.
- Format npz produksi: `W1` (1024,26), `b1`, `W2` (26,26 identitas), `b2`,
  `activation`, `temperature`, `bias`. Ada mekanisme varian lewat `activation`,
  tetapi itu untuk relu/linear di lapisan tersembunyi, BUKAN untuk fungsi
  keluaran.

Jadi kepala sigmoid tidak bisa dievaluasi lewat cascade hanya dengan menukar
berkas checkpoint.

## Dampak yang lebih dalam di cascade

`ml/engines/cascade.py` mengambil keputusan dengan `np.argsort(probs)` lalu
margin top1-top2:

1. Dengan kepala sigmoid, keluaran tiap kelas independen dan TIDAK berjumlah 1.
   Margin top1-top2 berubah arti, dan ambang per spesies hasil kalibrasi softmax
   tidak lagi sebanding.
2. Kelas `_negative` kehilangan maknanya. Inti kepala sigmoid justru "bukan
   spesies apa pun" = semua kepala rendah, bukan satu kelas khusus yang
   bersaing di dalam softmax.

## Konsekuensi untuk ML_10

K8 butuh tiga perubahan sekaligus: skrip latih, fungsi keluaran di engine, dan
kebijakan keputusan di cascade. ML_10 mensyaratkan satu kandidat satu perubahan
terhadap produksi, dan ML_00 melarang mengubah perilaku produksi tanpa gerbang.

Pilihan yang jujur, dua-duanya sah dilaporkan:

- Kerjakan K8 sebagai eksperimen di tingkat CV/embedding saja, tanpa menyentuh
  jalur produksi, lalu laporkan sebagai arah untuk putaran berikutnya.
- Lewati dan akui tidak sempat.

Yang TIDAK boleh: menambal softmax menjadi sigmoid di engine tanpa test paritas,
karena itu mengubah perilaku produksi tanpa gerbang dan memecahkan test paritas
8 klip demo (`ml/reports/paritas_07947bc.json`).

Catatan: `ml/train_ovr_calibrated.py` sudah ada tetapi hanya melaporkan angka;
penulisan checkpoint palsu berisi nol sudah dihapus di commit 2efecaa.
