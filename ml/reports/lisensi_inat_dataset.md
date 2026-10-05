# Lisensi iNatSounds (L6-5)

Tanggal akses: 30 September 2026

## Sumber yang diperiksa

1. Repositori resmi: https://github.com/visipedia/inat_sounds
   - Lisensi repo: MIT (berlaku untuk kode, bukan data)
   - README Terms of Use: "You accept full responsibility for your use of the
     data and shall defend and indemnify UMass Amherst, including its employees,
     officers and agents, against any and all claims arising from your use of
     the data, including but not limited to your use of any copies of
     copyrighted media that you may create from the data."
   - Tidak ada pernyataan lisensi per-rekaman (CC-BY, CC0, dll.)

2. Paper: Chasmai et al. "The iNaturalist Sounds Dataset" (arXiv:2506.00343v1,
   31 Mei 2025, NeurIPS 2024 Datasets and Benchmarks Track)
   - NeurIPS checklist: "All observations were approved by recordists for
     research use" (item 5.d)
   - Tidak memuat pernyataan lisensi per-rekaman di Section 6 atau appendix

3. HuggingFace: https://huggingface.co/datasets/DBD-research-group/inat_sounds
   - Tidak ada kartu dataset dengan pernyataan lisensi

4. Paper pembanding (InsectSet459, arXiv:2503.15074): "iNatSounds is made
   available under a 'terms of service' agreement with conditions of no
   commercial use, and no permission to redistribute, presumably because of
   considerations about the licensing of some of the included content."

## Kesimpulan

Sumber resmi TIDAK menyatakan secara eksplisit bahwa semua rekaman memakai
lisensi yang mengizinkan pemakaian non-komersial tanpa larangan turunan. Yang
ada hanya Terms of Use berupa indemnification clause dan konfirmasi NeurIPS
bahwa rekaman disetujui perekam untuk "research use".

Sesuai ML_06 L6-5: manifest TIDAK diperbarui, C17 TETAP GAGAL.

Berkas keluaran: `ml/reports/lisensi_inat_dataset.md`
