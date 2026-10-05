# Status Lampiran 2 (putaran B00-B06)

## Keluaran audit terakhir

```
audit_model.py sha256 b606df8d22488b45
[GAGAL] C01 ruff bersih                                          Found 2 errors.
[LULUS] C02 pytest ml/tests                                      15 passed in 13.28s
[LULUS] C03 test worker (container)                              31 passed, 3 warnings in 13.35s
[LULUS] C04 test API (container)                                 97 passed, 3 skipped, 1 warning in 13.81s
[LULUS] C05 checkpoint cocok MANIFEST                            ff01eb96e002
[LULUS] C06 thresholds.json datar dan terbaca muat_ambang        26 kunci
[LULUS] C07 fixture snapshot == mesin produksi                   selisih keyakinan maks 0.0000, label beda 0/10
[LULUS] C08 tidak ada pemilihan jendela/sampel memakai label
[LULUS] C09 uji independen produksi (tanpa label)                acc produksi tanpa label 0.7557 (n=131)
[LULUS] C10 CV bersarang: ambang di lipatan + CI bootstrap grup
[LULUS] C11 e2e: agregat konsisten dengan baris per berkas
[LULUS] C12 worker yang jalan memakai checkpoint repo            worker ff01eb96e002 repo ff01eb96e002

11 LULUS, 1 GAGAL, 0 BELUM
```

## Tabel B00-B06

| ID | Status | Detail |
|----|--------|--------|
| B00 | LULUS | audit_model.py sha cocok, audit awal 5L/6G/1B disimpan |
| B01 | LULUS | 2 error ruff uji_independen.py diperbaiki |
| B02 | LULUS | snapshot via engine produksi, C07 LULUS (selisih 0.0000) |
| B03 | LULUS | uji independen tanpa label, C08+C09 LULUS, koreksi.md |
| B04 | LULUS | CV bersarang lengkap, C10 LULUS |
| B05 | LULUS | e2e baseline, C11 LULUS |
| B06 | - | laporan ini |

## Angka baseline e2e

- Presisi 0,6172, recall 0,7619, spesies nontarget/berkas 0,8324
- CV bersarang OOF: acc 0,7383, F1 0,7288 (CI95 acc [0,7052, 0,7692], F1 [0,6897, 0,7506])
- Uji independen (tanpa label): acc 0,7557

## GAGAL / BLOCKED

C01 GAGAL: `ops/audit_model.py` baris 61 memakai semicolon (`tp=...; fp=...; fn=...`)
yang membuat `ruff check .` melaporkan 2 error E702. Lampiran 2 melarang mengubah
berkas ini, jadi C01 tak bisa LULUS tanpa perbaikan peninjau. Dicatat di
NEEDS_FROM_YOU.md.

## sha256 audit_model.py

- Awal: b606df8d22488b45bb26b970db29008055bf519e82084f661d3bbca29bb42d05
- Akhir: b606df8d22488b45bb26b970db29008055bf519e82084f661d3bbca29bb42d05
- Tidak berubah.
