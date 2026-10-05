# Pemicu deteksi palsu (L7-1)

Sumber: `docs/assets/data/e2e_produksi_385147c.json`, `ml/data/pembagian_openset.json`.
Baseline: paket produksi (checkpoint `ff01eb96`, ambang produksi, cascade produksi).
Semua deteksi jalur B (model lokal via Track B `CascadeEngine.predict`).

## Ringkasan

- FP pilih: 25/59 berkas other (0,424)
- FP lapor: 21/38 berkas other (0,553)
- 15 spesies pengecoh unik memicu deteksi target

## Tabel pemicu (urut berkas pilih, keputusan hanya dari pilih)

| # | Spesies pengecoh | Pilih | Lapor | Spesies target dituduhkan (jumlah) | Pola |
|---|---|---:|---:|---|---|
| 1 | Orthotomus ruficeps (Ashy Tailorbird) | 5 | 0 | Chalcophaps indica (1), Todiramphus chloris (1), Orthotomus sutorius (1), Hirundo tahitica (1), Centropus bengalensis (1) | Menyebar ke 5 target |
| 2 | Accipiter badius (Shikra) | 4 | 0 | Lonchura punctulata (2), Dicrurus macrocercus (2), Todiramphus chloris (1), Anthreptes malacensis (1) | Raptor tapi dituduh passerine |
| 3 | Dicaeum trochileum (Scarlet-headed Flowerpecker) | 4 | 0 | Geopelia striata (1), Cisticola juncidis (1), Lonchura punctulata (1), Hirundo tahitica (1) | Menyebar |
| 4 | Aethopyga mystacalis (Javan Sunbird) | 3 | 0 | Cinnyris jugularis (3), Anthreptes malacensis (1) | Sunbird -> Sunbird |
| 5 | Hemipus hirundinaceus (Black-winged Flycatcher-shrike) | 3 | 0 | Aplonis panayensis (1), Hirundo tahitica (1), Orthotomus sutorius (1) | Menyebar |
| 6 | Merops viridis (Blue-throated Bee-eater) | 3 | 0 | Merops philippinus (2), Geopelia striata (1) | Bee-eater -> Bee-eater |
| 7 | Centropus sinensis (Greater Coucal) | 2 | 0 | Centropus bengalensis (2), Chalcophaps indica (1), Gallus gallus (1) | Coucal -> Coucal |
| 8 | Dendrocygna arcuata (Wandering Whistling-Duck) | 1 | 0 | Lonchura punctulata (1) | Unrelated |
| 9 | Merops leschenaulti (Chestnut-headed Bee-eater) | 0 | 6 | Merops philippinus (5), Pycnonotus aurigaster (2), Todiramphus chloris (1) | Bee-eater -> Bee-eater |
| 10 | Aethopyga siparaja (Crimson Sunbird) | 0 | 4 | Cinnyris jugularis (3), Anthreptes malacensis (2), Aplonis panayensis (1) | Sunbird -> Sunbird |
| 11 | Lonchura leucogastroides (Javan Munia) | 0 | 3 | Hirundo tahitica (2), Spilopelia chinensis (1), Lonchura punctulata (1) | Munia -> Munia + lain |
| 12 | Lonchura maja (White-headed Munia) | 0 | 3 | Lonchura punctulata (2), Spilopelia chinensis (1) | Munia -> Munia |
| 13 | Corvus enca (Slender-billed Crow) | 0 | 2 | Corvus macrorhynchos (2) | Crow -> Crow |
| 14 | Pericrocotus cinnamomeus (Small Minivet) | 0 | 2 | Cinnyris jugularis (1), Pycnonotus aurigaster (1) | Menyebar |
| 15 | Pellorneum rostratum (White-chested Babbler) | 0 | 1 | Anthreptes malacensis (1) | - |

## Pola

1. Genus yang sama: 5 dari 15 pemicu adalah kerabat dekat target (Merops, Aethopyga,
   Lonchura, Centropus, Corvus). Softmax tidak bisa menolak suara yang mirip tapi
   bukan spesies target.

2. Menyebar ke banyak target: Orthotomus ruficeps dan Dicaeum trochileum memicu
   5 dan 4 target berbeda. Ini menunjukkan suara pendek bernada tinggi yang softmax
   paksa masuk ke kelas manapun dengan skor tertinggi.

3. Kandidat kelas baru (L7-4): spesies pengecoh yang sering memicu dan punya cukup
   data XC bisa dijadikan kelas sendiri, sehingga model bisa mengenali mereka
   daripada salah menyebutnya sebagai target.

## Perintah

```
python3 -c "import json; ..." < docs/assets/data/e2e_produksi_385147c.json
```

Berkas keluaran: `ml/reports/pemicu_palsu.md`
