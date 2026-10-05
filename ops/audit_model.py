#!/usr/bin/env python3
"""Audit independen model Track B GemaHutan, versi 2.

Ditulis peninjau, bukan oleh agen yang dinilai. Agen boleh menjalankan, tidak
boleh mengubah. sha256 berkas ini dicatat di prompt.

Status per pemeriksaan:
  LULUS    syarat terpenuhi, dihitung ulang oleh skrip ini
  GAGAL    syarat tidak terpenuhi, artefak salah, atau artefak wajib tidak ada
  MELESET  artefak benar, tetapi target mutu belum tercapai
  MANUSIA  menunggu pekerjaan manusia (data lapangan)
Kode keluar 1 kalau ada GAGAL.

Pakai (dari akar repo):
    .venv/bin/python ops/audit_model.py            # semua
    .venv/bin/python ops/audit_model.py --cepat    # lewati test docker
    .venv/bin/python ops/audit_model.py --json keluaran.json
"""
import argparse
import csv
import hashlib
import json
import os
import re
import subprocess
import sys
from pathlib import Path

import numpy as np

ROOT = Path(os.environ.get("GEMAHUTAN_ROOT") or Path(__file__).resolve().parent.parent)
sys.path.insert(0, str(ROOT))
ML = ROOT / "ml"
REP = ML / "reports"
DATA = ML / "data"
SHA_LR_V3 = "ff01eb96e002bb32d58120ea5c347cf6398c4b3435121f7b367e2a6dbbad808e"
EKSTENSI_AUDIO = {".wav", ".mp3", ".m4a", ".ogg", ".flac", ".opus", ".webm", ".aac"}
LISENSI_TERLARANG = ("nd", "lihat-berkas-asli", "all rights reserved", "unknown", "tidak diketahui", "")
ANGKA_USANG = ("924 klip", "0,7156", "0.7156", "3,4 kali", "3.4x", "218 klip")
hasil = []


def catat(kode, butir, nama, status, detail=""):
    hasil.append({"kode": kode, "butir": butir, "nama": nama, "status": status, "detail": str(detail)[:500]})


def jalankan(cmd, timeout=900):
    p = subprocess.run(cmd, shell=True, cwd=ROOT, capture_output=True, text=True, timeout=timeout)
    return p.returncode, (p.stdout + p.stderr).strip()


def ekor(teks, n=1):
    baris = [b for b in teks.splitlines() if b.strip() and not b.strip().startswith("Container ")]
    return " | ".join(baris[-n:])[:300]


def sha(p):
    return hashlib.sha256(Path(p).read_bytes()).hexdigest()


def baca_json(p):
    p = Path(p)
    return json.loads(p.read_text()) if p.exists() else None


def f1_makro(y, p, kelas):
    f = []
    for c in kelas:
        tp = np.sum((p == c) & (y == c))
        fp = np.sum((p == c) & (y != c))
        fn = np.sum((p != c) & (y == c))
        f.append(0.0 if tp == 0 else 2 * tp / (2 * tp + fp + fn))
    return float(np.mean(f))


def bootstrap_grup(y, P, g, fungsi, n=1000):
    rng = np.random.default_rng(0)
    grup = np.unique(g)
    idx_g = {k: np.where(g == k)[0] for k in grup}
    nilai = []
    for _ in range(n):
        ii = np.concatenate([idx_g[k] for k in rng.choice(grup, size=len(grup), replace=True)])
        nilai.append(fungsi(y[ii], P[ii]))
    return np.percentile(nilai, [2.5, 97.5])


# ------------------------------------------------------------------ C01-C04
def cek_test(cepat):
    rc, out = jalankan('docker run --rm -v "$PWD":/src -w /src gemahutan-api:latest python -m ruff check .')
    catat("C01", 1, "ruff bersih", "LULUS" if rc == 0 else "GAGAL", ekor(out, 2))
    rc, out = jalankan(f"{sys.executable} -m pytest -q ml/tests -p no:cacheprovider")
    catat("C02", 1, "pytest ml/tests", "LULUS" if rc == 0 else "GAGAL", ekor(out))
    if cepat:
        catat("C03", 1, "test worker (container)", "GAGAL", "dilewati --cepat; jalankan tanpa --cepat")
        catat("C04", 1, "test API (container)", "GAGAL", "dilewati --cepat; jalankan tanpa --cepat")
        return
    rc, out = jalankan('docker compose run --rm --no-deps -v "$PWD/apps/worker/tests:/app/tests" '
                       '-v "$PWD/ml:/app/ml" worker python -m pytest tests -q -p no:cacheprovider')
    catat("C03", 1, "test worker (container)", "LULUS" if rc == 0 else "GAGAL", ekor(out))
    rc, out = jalankan('docker compose run --rm --no-deps -v "$PWD/apps/api:/app" '
                       '-v "$PWD/ml:/app/ml" api python -m pytest tests -q -p no:cacheprovider')
    catat("C04", 1, "test API (container)", "LULUS" if rc == 0 else "GAGAL", ekor(out))


# ------------------------------------------------------------------ C05-C06
def cek_artefak():
    m = baca_json(ML / "checkpoints" / "MANIFEST.json")
    if not m:
        catat("C05", 1, "checkpoint cocok MANIFEST", "GAGAL", "MANIFEST.json tidak ada")
        return None
    salah = [n for n, v in m.get("files", {}).items()
             if not (ML / "checkpoints" / n).exists() or sha(ML / "checkpoints" / n) != v["sha256"]]
    sha_model = m["files"]["best_model.npz"]["sha256"]
    catat("C05", 1, "checkpoint cocok MANIFEST", "GAGAL" if salah else "LULUS",
          f"tidak cocok: {salah}" if salah else sha_model[:12])
    try:
        from ml.ambang import muat_ambang
        a = muat_ambang(REP / "thresholds.json")
        nilai = sorted(a.values())
        med = nilai[len(nilai) // 2]
        ok = med >= 0.05 and sum(v <= 0.0 for v in nilai) == 0
        catat("C06", 1, "thresholds.json terbaca dan masuk akal", "LULUS" if ok else "GAGAL",
              f"{len(a)} kunci, median {med:.3f}, nol {sum(v <= 0.0 for v in nilai)}")
    except Exception as exc:  # noqa: BLE001
        catat("C06", 1, "thresholds.json terbaca dan masuk akal", "GAGAL", exc)
    return m


def mesin_produksi():
    from ml.engines.embedding_clf import EmbeddingClassifierEngine
    EmbeddingClassifierEngine._load_birdnet_interpreter = lambda self: None
    e = EmbeddingClassifierEngine()
    e._ensure_loaded()
    return e


def prob_produksi(e, emb):
    x = (np.asarray(emb, dtype=np.float32) - e._mean) / e._std
    return e._calibrated_probs(x.reshape(-1, x.shape[-1]))


# ------------------------------------------------------------------ C07
def cek_snapshot(e):
    d = baca_json(ROOT / "apps/api/tests/fixtures/model_snapshots.json")
    if not d:
        catat("C07", 1, "fixture snapshot == mesin produksi", "GAGAL", "fixture tidak ada")
        return
    maks, beda = 0.0, 0
    for c in d["clips"]:
        p = prob_produksi(e, c["embedding"])[0]
        k = int(np.argmax(p))
        beda += e._inv_label_map[k] != c["expected_label"]
        maks = max(maks, abs(float(p[k]) - float(c["expected_confidence"])))
    catat("C07", 1, "fixture snapshot == mesin produksi", "LULUS" if maks <= 1e-3 and beda == 0 else "GAGAL",
          f"selisih maks {maks:.4f}, label beda {beda}/{len(d['clips'])}")


# ------------------------------------------------------------------ C08
POLA_BOCOR = re.compile(
    r"arg(max|sort)\s*\(\s*[\w\.]+\s*\[\s*:\s*,\s*(target|y|y_true|label|kelas_benar|y_te\w*|y_val\w*)\s*\]")


def cek_bocor_label():
    temuan = []
    for f in sorted(list(ML.glob("*.py")) + list((ML / "data").glob("*.py"))):
        for i, baris in enumerate(f.read_text(errors="ignore").splitlines(), 1):
            if POLA_BOCOR.search(baris):
                temuan.append(f"{f.relative_to(ROOT)}:{i}")
    catat("C08", 3, "tidak ada pemilihan memakai label", "GAGAL" if temuan else "LULUS", ", ".join(temuan[:6]))


# ------------------------------------------------------------------ C09
def cek_independen(e, sha_model):
    man, cache = DATA / "uji_independen/manifest.csv", DATA / "uji_independen/embedding_cache"
    if not man.exists() or not cache.exists():
        catat("C09", 3, "uji independen produksi (tanpa label)", "GAGAL", "data tidak ada")
        return None
    lm = e._label_map
    tgt = [k for k in range(len(lm)) if k != lm.get("_negative")]
    y, p = [], []
    for r in csv.DictReader(open(man)):
        f = cache / f"{r['clip_id']}.npy"
        if r["species_scientific"] not in lm or not f.exists():
            continue
        P = prob_produksi(e, np.load(f))
        w = int(np.unravel_index(np.argmax(P[:, tgt]), P[:, tgt].shape)[0])
        y.append(lm[r["species_scientific"]])
        p.append(int(np.argmax(P[w])))
    y, p = np.array(y), np.array(p)
    acc = float(np.mean(y == p))
    f1 = f1_makro(y, p, np.unique(y))
    j = baca_json(REP / "uji_independen.json") or {}
    masalah = []
    if j.get("metode_pemilihan_jendela") != "tanpa_label":
        masalah.append("metode_pemilihan_jendela bukan 'tanpa_label'")
    if j.get("sha256_checkpoint") != sha_model:
        masalah.append("sha256_checkpoint laporan bukan checkpoint produksi sekarang")
    lap = (j.get("jendela_terbaik") or {}).get("acc")
    if lap is None or abs(lap - acc) > 0.005:
        masalah.append(f"laporan acc {lap} vs dihitung {acc:.4f}")
    catat("C09", 3, "uji independen produksi (tanpa label)", "GAGAL" if masalah else "LULUS",
          f"acc {acc:.4f}, F1 {f1:.4f}, n={len(y)}; " + "; ".join(masalah))
    return {"acc": acc, "f1": f1}


# ------------------------------------------------------------------ C10
def cek_bersarang():
    j, npz = baca_json(REP / "eval_bersarang.json"), REP / "oof_bersarang.npz"
    if not j or not npz.exists():
        catat("C10", 3, "CV bersarang valid", "GAGAL", "eval_bersarang.json atau oof_bersarang.npz tidak ada")
        return None
    d = np.load(npz, allow_pickle=False)
    P, y, g, lip = d["probs"], d["y"], d["grup"], d["lipatan"]
    kelas = np.unique(y)
    masalah = []
    f1 = f1_makro(y, P.argmax(1), kelas)
    if abs(((j.get("aggregat") or {}).get("f1_macro") or -9) - f1) > 0.01:
        masalah.append(f"F1 OOF {f1:.4f} vs laporan {(j.get('aggregat') or {}).get('f1_macro')}")
    ci = j.get("ci95") or {}
    lo, hi = bootstrap_grup(y, P, g, lambda a, b: f1_makro(a, b.argmax(1), kelas))
    lap = ci.get("f1_macro") or {}
    if ci.get("metode") != "bootstrap_grup_perekam" or abs(lap.get("ci95_low", -9) - lo) > 0.02 \
            or abs(lap.get("ci95_high", -9) - hi) > 0.02:
        masalah.append(f"CI F1 [{lo:.3f}, {hi:.3f}] vs laporan {lap}")
    lipatan = {int(x["lipatan"]): x for x in j.get("lipatan") or []}
    geser = 1 if (len(lip) and int(lip.min()) == 0 and 0 not in lipatan) else 0
    tp = fp = fn = 0
    nol, total_amb = 0, 0
    for i in range(len(y)):
        x = lipatan.get(int(lip[i]) + geser)
        amb = (x or {}).get("ambang")
        if not isinstance(amb, dict) or len(amb) < 25:
            masalah.append("lipatan tanpa 25 ambang")
            break
        for nama, k in LABEL_MAP.items():
            if nama == "_negative":
                continue
            pr, pos = P[i, k] >= amb.get(nama, 1.1), y[i] == k
            tp += pr and pos
            fp += pr and not pos
            fn += (not pr) and pos
    for x in lipatan.values():
        for v in (x.get("ambang") or {}).values():
            total_amb += 1
            nol += v <= 0.0
    presisi, recall = tp / max(tp + fp, 1), tp / max(tp + fn, 1)
    pa = j.get("aggregat_pada_ambang") or {}
    if abs(pa.get("presisi", -9) - presisi) > 0.01 or abs(pa.get("recall", -9) - recall) > 0.01:
        masalah.append(f"pada ambang dihitung presisi {presisi:.3f} recall {recall:.3f} vs laporan {pa}")
    if total_amb and nol / total_amb > 0.1:
        masalah.append(f"{nol}/{total_amb} ambang bernilai 0")
    if presisi < 0.5:
        masalah.append(f"presisi pada ambang {presisi:.3f} < 0,5: ambang tidak masuk akal")
    catat("C10", 3, "CV bersarang valid", "GAGAL" if masalah else "LULUS",
          f"F1 {f1:.4f} [{lo:.3f}, {hi:.3f}], pada ambang P {presisi:.3f} R {recall:.3f}; " + "; ".join(masalah))
    return {"f1": f1, "lo": lo, "hi": hi}


# ------------------------------------------------------------------ C11
def daftar_audio_berlabel():
    out = {}
    for korpus in ("inat", "xc_noisy", "other"):
        for f in (DATA / "field/audio" / korpus).rglob("*"):
            if f.suffix.lower() in EKSTENSI_AUDIO:
                out[str(f.relative_to(DATA))] = f"field/{korpus}"
    man = DATA / "uji_independen/manifest.csv"
    if man.exists():
        berlabel = {r["clip_id"] for r in csv.DictReader(open(man)) if r["species_scientific"] in LABEL_MAP}
        for f in (DATA / "uji_independen/audio").rglob("*"):
            if f.suffix.lower() in EKSTENSI_AUDIO and f.stem in berlabel:
                out[str(f.relative_to(DATA))] = "uji_independen"
    return out


def metrik_berkas(rows):
    tp = sum(len(set(r["terdeteksi"]) & set(r["benar"])) for r in rows)
    fp = sum(len(set(r["terdeteksi"]) - set(r["benar"])) for r in rows)
    fn = sum(len(set(r["benar"]) - set(r["terdeteksi"])) for r in rows)
    return tp / max(tp + fp, 1), tp / max(tp + fn, 1)


def cek_e2e(sha_model):
    j = baca_json(REP / "e2e.json")
    if not j:
        catat("C11", 4, "e2e lengkap dan konsisten", "GAGAL", "e2e.json tidak ada")
        return None
    rows, gagal = j.get("per_berkas") or [], j.get("gagal") or []
    masalah = []
    if j.get("jalur") != "CascadeEngine.predict":
        masalah.append("jalur bukan CascadeEngine.predict")
    if j.get("sha256_checkpoint") != sha_model:
        masalah.append("sha256_checkpoint bukan checkpoint produksi sekarang")
    semua = daftar_audio_berlabel()
    tercakup = {r["berkas"] for r in rows} | {x.get("berkas") for x in gagal}
    hilang = [b for b in semua if b not in tercakup]
    if hilang:
        masalah.append(f"{len(hilang)} berkas tidak dievaluasi dan tidak dicatat gagal, mis. {hilang[:2]}")
    if semua and len(gagal) / len(semua) > 0.03:
        masalah.append(f"gagal dekode {len(gagal)}/{len(semua)} > 3 persen")
    if any("bagian" not in r for r in rows):
        masalah.append("baris per_berkas tanpa kunci 'bagian' (pilih/lapor)")
    pres, rec = metrik_berkas(rows)
    lap = j.get("agregat") or {}
    if abs(lap.get("presisi", -9) - pres) > 0.005 or abs(lap.get("recall", -9) - rec) > 0.005:
        masalah.append(f"agregat dihitung P {pres:.4f} R {rec:.4f} vs laporan {lap}")
    catat("C11", 4, "e2e lengkap dan konsisten", "GAGAL" if masalah else "LULUS",
          f"{len(rows)} dievaluasi, {len(gagal)} gagal, {len(semua)} berkas berlabel; P {pres:.3f} R {rec:.3f}; "
          + "; ".join(masalah))
    return rows


# ------------------------------------------------------------------ C12
def cek_worker():
    rc, out = jalankan("docker compose exec -T worker sha256sum /app/ml/checkpoints/best_model.npz", timeout=60)
    if rc != 0:
        catat("C12", 1, "worker memakai checkpoint repo", "GAGAL", "worker tidak bisa dihubungi")
        return
    repo = sha(ML / "checkpoints/best_model.npz")
    catat("C12", 1, "worker memakai checkpoint repo", "LULUS" if out.split()[0] == repo else "GAGAL",
          f"worker {out.split()[0][:12]} repo {repo[:12]}")


# ------------------------------------------------------------------ C13-C15 mutu
def cek_openset(rows):
    bag = baca_json(DATA / "pembagian_openset.json")
    if rows is None or not bag:
        catat("C13", 6, "open-set: FP pengecoh <= 0,15 & recall >= 0,70 (bagian lapor)", "GAGAL",
              "e2e.json atau ml/data/pembagian_openset.json tidak ada")
        return
    sp_pilih = set(bag.get("spesies_pengecoh_pilih") or [])
    sp_lapor = set(bag.get("spesies_pengecoh_lapor") or [])
    if not sp_pilih or not sp_lapor or sp_pilih & sp_lapor:
        catat("C13", 6, "open-set: FP pengecoh <= 0,15 & recall >= 0,70 (bagian lapor)", "GAGAL",
              "spesies pengecoh pilih/lapor kosong atau beririsan")
        return
    peng = [r for r in rows if r["korpus"] == "field/other" and r.get("bagian") == "lapor"]
    for r in peng:
        folder = Path(r["berkas"]).parent.name.replace("_", " ")
        if folder in sp_pilih:
            catat("C13", 6, "open-set", "GAGAL", f"berkas pengecoh lapor dari spesies pilih: {r['berkas']}")
            return
    targ = [r for r in rows if r["korpus"] != "field/other" and (r.get("bagian") == "lapor"
                                                                 or r["korpus"] == "uji_independen")]
    if not peng or not targ:
        catat("C13", 6, "open-set", "GAGAL", "bagian lapor kosong")
        return
    fp_berkas = sum(1 for r in peng if r["terdeteksi"]) / len(peng)
    _, rec = metrik_berkas(targ)
    ok = fp_berkas <= 0.15 and rec >= 0.70
    catat("C13", 6, "open-set: FP pengecoh <= 0,15 & recall >= 0,70 (bagian lapor)", "LULUS" if ok else "MELESET",
          f"berkas pengecoh berdeteksi {fp_berkas:.3f} (n={len(peng)}), recall target {rec:.3f} (n={len(targ)})")


def cek_mutu(cv, ind, rows):
    if cv is None or ind is None:
        catat("C14", 5, "mutu classifier: F1 CV >= 0,78, CI bawah >= 0,75, independen F1 >= 0,75", "GAGAL",
              "C09/C10 belum valid")
    else:
        ok = cv["f1"] >= 0.78 and cv["lo"] >= 0.75 and ind["f1"] >= 0.75
        catat("C14", 5, "mutu classifier: F1 CV >= 0,78, CI bawah >= 0,75, independen F1 >= 0,75",
              "LULUS" if ok else "MELESET",
              f"F1 CV {cv['f1']:.3f} [{cv['lo']:.3f}], independen F1 {ind['f1']:.3f}")
    if rows is None:
        catat("C15", 6, "ponsel iNat e2e: presisi >= 0,75 & recall >= 0,62", "GAGAL", "e2e tidak valid")
        return
    inat = [r for r in rows if r["korpus"] == "field/inat" and r.get("bagian") == "lapor"]
    if not inat:
        catat("C15", 6, "ponsel iNat e2e: presisi >= 0,75 & recall >= 0,62", "GAGAL", "tidak ada baris iNat lapor")
        return
    p, r = metrik_berkas(inat)
    catat("C15", 6, "ponsel iNat e2e: presisi >= 0,75 & recall >= 0,62",
          "LULUS" if p >= 0.75 and r >= 0.62 else "MELESET", f"P {p:.3f} R {r:.3f} (n={len(inat)})")


# ------------------------------------------------------------------ C16 operasi
def cek_latensi():
    j = baca_json(REP / "latensi.json")
    if not j:
        catat("C16", 7, "latensi 60 menit < 900 dtk, RSS < 1800 MB, BirdNET 1x", "GAGAL", "latensi.json tidak ada")
        return
    masalah = []
    if j.get("durasi_audio_s", 0) < 3600:
        masalah.append("benchmark < 60 menit audio")
    if j.get("sha256_checkpoint") != sha(ML / "checkpoints/best_model.npz"):
        masalah.append("benchmark bukan checkpoint produksi")
    if j.get("invoke_birdnet_per_segmen") != 1:
        masalah.append(f"invoke BirdNET per segmen {j.get('invoke_birdnet_per_segmen')}")
    if j.get("identik_8_demo") is not True:
        masalah.append("deteksi 8 klip demo tidak dinyatakan identik")
    ok_angka = j.get("waktu_s", 1e9) < 900 and j.get("rss_maks_mb", 1e9) < 1800
    status = "GAGAL" if masalah else ("LULUS" if ok_angka else "MELESET")
    catat("C16", 7, "latensi 60 menit < 900 dtk, RSS < 1800 MB, BirdNET 1x", status,
          f"waktu {j.get('waktu_s')} dtk, RSS {j.get('rss_maks_mb')} MB; " + "; ".join(masalah))


# ------------------------------------------------------------------ C17 lisensi
def cek_lisensi(m):
    meta = baca_json(ML / "checkpoints/meta.json") or {}
    splits = meta.get("splits_file")
    man = DATA / "manifest_latih_produksi.csv"
    if not splits or not man.exists() or not (ROOT / splits).exists():
        catat("C17", 8, "lisensi tiap klip latih produksi sah", "GAGAL",
              "meta.json tanpa splits_file, atau ml/data/manifest_latih_produksi.csv tidak ada")
        return
    sp = json.loads((ROOT / splits).read_text())
    latih = set(sp.get("train", [])) | set(sp.get("val", []))
    lis = {r["clip_id"]: (r.get("license") or "").strip().lower() for r in csv.DictReader(open(man))}
    tanpa = [c for c in latih if c not in lis]
    buruk = [c for c in latih if c in lis and (lis[c] in LISENSI_TERLARANG or "-nd" in lis[c] or "/nd" in lis[c])]
    catat("C17", 8, "lisensi tiap klip latih produksi sah", "GAGAL" if tanpa or buruk else "LULUS",
          f"{len(latih)} klip latih, tanpa baris {len(tanpa)}, lisensi terlarang {len(buruk)}")


# ------------------------------------------------------------------ C18 jendela latih
def cek_jendela():
    j = baca_json(REP / "pemilihan_jendela.json")
    if not j:
        catat("C18", 8, "label lemah ditangani (bukan 3 detik pertama)", "GAGAL", "pemilihan_jendela.json tidak ada")
        return
    meta = baca_json(ML / "checkpoints/meta.json") or {}
    ok = j.get("metode") not in (None, "", "tiga_detik_pertama") and meta.get("emb_dir") == j.get("emb_dir")
    catat("C18", 8, "label lemah ditangani (bukan 3 detik pertama)", "LULUS" if ok else "GAGAL",
          f"metode {j.get('metode')}, emb_dir laporan {j.get('emb_dir')}, produksi {meta.get('emb_dir')}")


# ------------------------------------------------------------------ C19 gerbang
def cek_gerbang(m):
    if m is None:
        return
    s = m["files"]["best_model.npz"]["sha256"]
    if s == SHA_LR_V3:
        catat("C19", 1, "promosi model lewat gerbang", "LULUS", "produksi masih LR v3 asli")
        return
    g = baca_json(ROOT / (m.get("source_run") or "x") / "gerbang.json")
    ok = bool(g) and g.get("lulus") is True and g.get("sha256_checkpoint") == s
    catat("C19", 1, "promosi model lewat gerbang", "LULUS" if ok else "GAGAL",
          f"source_run {m.get('source_run')}, gerbang {'ada' if g else 'tidak ada'}")


# ------------------------------------------------------------------ C20 angka resmi
def cek_angka(cv, ind):
    r = baca_json(REP / "angka_resmi.json")
    masalah = []
    if not r:
        masalah.append("angka_resmi.json tidak ada")
    else:
        if cv and abs((r.get("f1_cv") or -9) - cv["f1"]) > 0.005:
            masalah.append(f"f1_cv {r.get('f1_cv')} vs {cv['f1']:.4f}")
        if ind and abs((r.get("acc_independen") or -9) - ind["acc"]) > 0.005:
            masalah.append(f"acc_independen {r.get('acc_independen')} vs {ind['acc']:.4f}")
    berkas = [ROOT / "README.md", REP / "eval.md", ROOT / "apps/api/app/services/model_status.py"] + \
        list((ROOT / "docs/proposal").glob("*.md"))
    for b in berkas:
        if b.exists():
            teks = b.read_text(errors="ignore")
            for u in ANGKA_USANG:
                if u in teks:
                    masalah.append(f"'{u}' di {b.relative_to(ROOT)}")
    if r and cv:
        f1s = f"{r.get('f1_cv', 0):.3f}"
        if f1s not in (ROOT / "README.md").read_text() and f1s.replace(".", ",") not in (ROOT / "README.md").read_text():
            masalah.append(f"README tidak memuat f1_cv {f1s}")
    catat("C20", 9, "satu sumber angka, tidak ada angka usang", "GAGAL" if masalah else "LULUS",
          "; ".join(masalah[:6]))


# ------------------------------------------------------------------ C21 lapangan
def cek_lapangan():
    q = ("SELECT COALESCE(SUM(r.duration_s),0)/60.0, COUNT(DISTINCT d.id) FROM detections d "
         "JOIN recordings r ON r.id = d.recording_id WHERE d.verified_status <> 'unverified' "
         "AND COALESCE(r.original_filename, '') NOT LIKE 'xc-%'")
    rc, out = jalankan(f'docker compose exec -T db psql -U gemahutan -d gemahutan -At -c "{q}"', timeout=60)
    if rc != 0:
        catat("C21", 10, "data lapangan asli >= 30 menit terverifikasi", "MANUSIA", "database tidak bisa dihubungi")
        return
    menit, n = (float(x or 0) for x in out.split("|"))
    j = baca_json(REP / "lapangan_asli.json")
    if menit >= 30 and n >= 50:
        ok = bool(j) and abs(j.get("menit_terverifikasi", -9) - menit) < 1
        catat("C21", 10, "data lapangan asli >= 30 menit terverifikasi", "LULUS" if ok else "GAGAL",
              f"{menit:.1f} menit, {n:.0f} deteksi terverifikasi; laporan {'ada' if j else 'tidak ada'}")
    else:
        catat("C21", 10, "data lapangan asli >= 30 menit terverifikasi", "MANUSIA",
              f"baru {menit:.1f} menit, {n:.0f} deteksi terverifikasi di DB")


# ------------------------------------------------------------------ C22 reproduksi
def cek_reproduksi(m):
    masalah = []
    mk = ROOT / "Makefile"
    if not mk.exists() or not re.search(r"^model-produksi:", mk.read_text(), re.M):
        masalah.append("Makefile tanpa target model-produksi")
    if m is None or "save_logreg" in str(m.get("build_command", "")) or not m.get("build_command"):
        if m is None or m["files"]["best_model.npz"]["sha256"] != SHA_LR_V3:
            masalah.append("MANIFEST.build_command tidak menunjuk perintah reproduksi")
    tr = ML / "tests/test_resep.py"
    if not tr.exists() or "0.005" not in tr.read_text():
        masalah.append("test_resep.py tanpa syarat selisih 0.005")
    catat("C22", 2, "reproduksi satu perintah", "GAGAL" if masalah else "LULUS", "; ".join(masalah))


LABEL_MAP = {}


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--cepat", action="store_true")
    ap.add_argument("--json")
    a = ap.parse_args()
    print(f"audit_model.py v2 sha256 {sha(__file__)[:16]}")
    cek_test(a.cepat)
    m = cek_artefak()
    e = mesin_produksi()
    LABEL_MAP.update(e._label_map)
    sha_model = sha(ML / "checkpoints/best_model.npz")
    cek_snapshot(e)
    cek_bocor_label()
    ind = cek_independen(e, sha_model)
    cv = cek_bersarang()
    rows = cek_e2e(sha_model)
    cek_worker()
    cek_openset(rows)
    cek_mutu(cv, ind, rows)
    cek_latensi()
    cek_lisensi(m)
    cek_jendela()
    cek_gerbang(m)
    cek_angka(cv, ind)
    cek_lapangan()
    cek_reproduksi(m)

    hasil.sort(key=lambda h: h["kode"])
    lebar = max(len(h["nama"]) for h in hasil)
    for h in hasil:
        print(f"[{h['status']:7}] {h['kode']} (butir {h['butir']:>2}) {h['nama']:<{lebar}}  {h['detail']}")
    hitung = {s: sum(h["status"] == s for h in hasil) for s in ("LULUS", "GAGAL", "MELESET", "MANUSIA")}
    per_butir = {}
    for h in hasil:
        per_butir.setdefault(h["butir"], []).append(h["status"])
    butir_lulus = sorted(b for b, s in per_butir.items() if all(x == "LULUS" for x in s))
    print(f"\n{hitung['LULUS']} LULUS, {hitung['GAGAL']} GAGAL, {hitung['MELESET']} MELESET, {hitung['MANUSIA']} MANUSIA")
    print(f"Butir rubrik yang lulus penuh: {butir_lulus} -> {len(butir_lulus)}/10")
    if a.json:
        Path(a.json).write_text(json.dumps({"hasil": hasil, "butir_lulus": butir_lulus}, indent=2, ensure_ascii=False))
    return 1 if hitung["GAGAL"] else 0


if __name__ == "__main__":
    sys.exit(main())
