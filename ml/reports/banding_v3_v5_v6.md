# Banding produksi, v5, v6 (G2)

Baseline = paket produksi (checkpoint ff01eb96, ambang produksi, cascade produksi).
Diukur ulang di A1 ML_07 karena banding lama memakai ambang yang disetel ulang
sebagai "v3", bukan ambang produksi.

Pool yang dipakai:
- E2E sha256 daftar berkas: 663d9ce53990808753ebc6b835b1319cbb567ffb97eaca36b092c0dcd29cdb16
- CV XC sha256 id: 2c3a5bfae796a2323096a6c46b52e874464236ce03de0dc0dd4cd17084cbc8bc
- Independen sha256 clip id: 4d3eae31d86601b536a2693ce6794773c06b49b0c8d0a8b0ff90f92de5bb2d5f

| Model | F1 CV | delta | FP lapor | delta FP | Recall target lapor | delta recall | Acc independen | delta acc | G2 |
|---|---:|---:|---:|---:|---:|---:|---:|---:|---|
| produksi | 0.7288 | 0.0000 | 21/38 (0.5526) | 0.0000 | 0.6870 | 0.0000 | 0.7557 | 0.0000 | baseline |
| v3 ambang ulang | 0.7288 | 0.0000 | 26/38 (0.6842) | +0.1316 | 0.6957 | +0.0087 | 0.7557 | 0.0000 | informasi |
| v5 | 0.7280 | -0.0008 | 28/38 (0.7368) | +0.1842 | 0.6609 | -0.0261 | 0.7405 | -0.0152 | GAGAL |
| v6 | 0.7338 | +0.0050 | 29/38 (0.7632) | +0.2105 | 0.7043 | +0.0174 | 0.7557 | +0.0000 | GAGAL |

Catatan: "v3 ambang ulang" = checkpoint produksi yang sama, dengan ambang dari
`ml/reports_logreg_v3/thresholds.json` (26 nilai berbeda dari ambang produksi).
FP lapor naik dari 21 ke 26 (+5 berkas), recall naik 0,0087. Ambang produksi
yang kasar menghasilkan 5 deteksi palsu lebih sedikit dengan recall hampir sama.

## Status syarat G2 (terhadap produksi)

### v5
- G2-1 F1 CV: LULUS (delta -0.0008, batas -0.02)
- G2-2 FP lapor: GAGAL (naik 21 -> 28, +7 berkas)
- G2-3 Recall lapor: GAGAL (turun 0.6870 -> 0.6609, delta -0.0261 > 0.03)
- G2-4 Acc independen: LULUS (delta -0.0152, batas -0.03)
- G2-5 F1 CV per spesies: LULUS
- G2-6 C01-C12: TIDAK DINILAI (G2-2 dan G2-3 gagal)

### v6
- G2-1 F1 CV: LULUS (delta +0.0050)
- G2-2 FP lapor: GAGAL (naik 21 -> 29, +8 berkas)
- G2-3 Recall lapor: LULUS (delta +0.0174)
- G2-4 Acc independen: LULUS (delta 0.0000)
- G2-5 F1 CV per spesies: LULUS
- G2-6 C01-C12: TIDAK DINILAI (G2-2 gagal)
