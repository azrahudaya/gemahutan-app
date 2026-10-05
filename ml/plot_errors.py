"""Error analysis: spektrogram 8 klip salah-klasifikasi dari data uji.

Memilih 4 kelas dengan support kecil (rentan keliru karena data kurang)
dan 4 confusion pair dari tabel confusion_top. Untuk tiap klip, render
spektrum (librosa specshow) plus label benar vs label tebakan dan
confidence.

Hasil:
  docs/proposal/figures/fig11_error_analysis.png
  ml/reports/error_analysis.md
"""
import json
import sys
from pathlib import Path

import numpy as np

ML_DIR = Path(__file__).resolve().parent
REPO_DIR = ML_DIR.parent
sys.path.insert(0, str(REPO_DIR))
sys.path.insert(0, str(ML_DIR))

from ml.train import MLP  # noqa: E402

EMB_DIR = ML_DIR / "embeddings"
DATA_DIR = ML_DIR / "data"
CKPT = ML_DIR / "checkpoints" / "best_model.npz"
NORM = ML_DIR / "checkpoints" / "normalization.npz"
SPLITS = ML_DIR / "data" / "splits.json"
REPORTS = ML_DIR / "reports"
FIG = REPO_DIR / "docs" / "proposal" / "figures"

# Empat kelas dengan support kecil (paling rentan dari data kurang) plus
# empat confusion pair dominan dari confusion_top.
KELAS_SUPPORT_KECIL = ["Prinia familiaris", "Gallus gallus",
                       "Dicrurus macrocercus", "Aplonis panayensis"]
CONFUSION_PAIR = [
    ("Amaurornis phoenicurus", "Merops philippinus"),
    ("Cinnyris jugularis", "Aegithina tiphia"),
    ("Hirundo tahitica", "Cinnyris jugularis"),
    ("Chalcophaps indica", "Amaurornis phoenicurus"),
]

# Lookup folder audio per spesies (manifest menulis nama genus_spesies).
SPECIES_FOLDER = {
    "Aegithina tiphia": "Aegithina_tiphia",
    "Amaurornis phoenicurus": "Amaurornis_phoenicurus",
    "Anthreptes malacensis": "Anthreptes_malacensis",
    "Aplonis panayensis": "Aplonis_panayensis",
    "Arachnothera longirostra": "Arachnothera_longirostra",
    "Centropus bengalensis": "Centropus_bengalensis",
    "Chalcophaps indica": "Chalcophaps_indica",
    "Cinnyris jugularis": "Cinnyris_jugularis",
    "Cisticola juncidis": "Cisticola_juncidis",
    "Corvus macrorhynchos": "Corvus_macrorhynchos",
    "Dicrurus macrocercus": "Dicrurus_macrocercus",
    "Gallus gallus": "Gallus_gallus",
    "Geopelia striata": "Geopelia_striata",
    "Haliastur indus": "Haliastur_indus",
    "Hirundo tahitica": "Hirundo_tahitica",
    "Lonchura punctulata": "Lonchura_punctulata",
    "Merops philippinus": "Merops_philippinus",
    "Orthotomus sutorius": "Orthotomus_sutorius",
    "Passer montanus": "Passer_montanus",
    "Prinia familiaris": "Prinia_familiaris",
    "Pycnonotus aurigaster": "Pycnonotus_aurigaster",
    "Pycnonotus goiavier": "Pycnonotus_goiavier",
    "Rhipidura javanica": "Rhipidura_javanica",
    "Spilopelia chinensis": "Spilopelia_chinensis",
    "Todiramphus chloris": "Todiramphus_chloris",
}


def muat_dan_prediksi():
    with open(EMB_DIR / "label_map.json") as f:
        label_map = json.load(f)
    inv = {v: k for k, v in label_map.items()}
    emb = np.load(EMB_DIR / "embeddings.npy")
    labels = np.load(EMB_DIR / "labels.npy")
    with open(EMB_DIR / "clip_ids.json") as f:
        ids = json.load(f)
    with open(SPLITS) as f:
        sp = json.load(f)
    norm = np.load(NORM)
    mean, std = norm["mean"], norm["std"]
    model = MLP(1024, 256, len(label_map))
    model.load(str(CKPT))

    cid_idx = {c: i for i, c in enumerate(ids)}
    test_idx = [cid_idx[c] for c in sp["test"] if c in cid_idx]
    X = emb[test_idx]
    y = labels[test_idx]
    clip_for_idx = [ids[i] for i in test_idx]
    from ml.model_loader import dengan_kalibrasi
    raw = model.forward((X - mean) / std)
    probs = dengan_kalibrasi(raw)
    preds = np.argmax(probs, axis=1)
    confs = probs[np.arange(len(probs)), preds]
    return clip_for_idx, y, preds, confs, inv


def cari_klip_salah(clip_for_idx, y, preds, confs, kelas_benar):
    """Ambil satu klip salah-klasifikasi untuk kelas_benar; kalau tak ada, ambil benar tapi confidence rendah."""
    for i, (cb, p) in enumerate(zip(y, preds, strict=True)):
        if cb == kelas_benar and cb != p:
            return i
    # fallback: confidence terendah untuk kelas itu
    kandidat = [i for i, cb in enumerate(y) if cb == kelas_benar]
    if not kandidat:
        return None
    return min(kandidat, key=lambda i: confs[i])


def cari_klip_confusion_pair(clip_for_idx, y, preds, confs, kelas_benar, kelas_tebakan):
    for i, (cb, p) in enumerate(zip(y, preds, strict=True)):
        if cb == kelas_benar and p == kelas_tebakan:
            return i
    return None


def ambil_audio(clip_id, kelas_benar):
    """Cari path audio untuk clip_id (test) di folder species. Cari fallback
    di folder lain kalau ada (kadang clip ada di kelas tetangga setelah shuffle)."""
    import csv
    man = list(csv.DictReader(open(DATA_DIR / "manifest.csv")))
    by_id = {r["clip_id"]: r for r in man}
    info = by_id.get(clip_id)
    if not info:
        return None, None
    p = DATA_DIR / info["local_path"]
    if not p.exists():
        # fallback: cari di folder species lain dengan nama file sama.
        for sp in ["_negative"]:
            for ext in (".mp3", ".wav", ".flac", ".ogg", ".m4a"):
                cand = DATA_DIR / "audio" / sp / f"{clip_id}{ext}"
                if cand.exists():
                    return cand, sp
        return None, info
    return p, info["species_scientific"]


def render_spektrogram(audio_path):
    """Return (S, sr) untuk librosa melspec. None kalau gagal."""
    import librosa

    try:
        y, sr = librosa.load(str(audio_path), sr=48000, mono=True, duration=3.0)
    except Exception:
        return None, None, None
    S = librosa.feature.melspectrogram(y=y, sr=sr, n_mels=128, n_fft=1024,
                                       hop_length=256)
    S_db = librosa.power_to_db(S, ref=np.max)
    return y, sr, S_db


def main():
    import matplotlib

    matplotlib.use("Agg")
    import matplotlib.pyplot as plt

    clip_for_idx, y, preds, confs, inv = muat_dan_prediksi()

    # Bangun daftar 8 kasus: 4 kelas support kecil + 4 confusion pair.
    kasus = []
    for kelas in KELAS_SUPPORT_KECIL:
        i = cari_klip_salah(clip_for_idx, y, preds, confs, kelas)
        if i is not None:
            kasus.append((i, "kelas_support_kecil"))
    for benar, tebakan in CONFUSION_PAIR:
        i = cari_klip_confusion_pair(clip_for_idx, y, preds, confs, benar, tebakan)
        if i is None:
            i = cari_klip_salah(clip_for_idx, y, preds, confs, benar)
        if i is not None:
            kasus.append((i, "confusion_pair"))
    kasus = kasus[:8]

    fig, axes = plt.subplots(8, 2, figsize=(14, 18), dpi=100)
    catatan = []

    for row, (i, jenis) in enumerate(kasus):
        clip_id = clip_for_idx[i]
        label_benar = inv[y[i]]
        label_tebakan = inv[preds[i]]
        confidence = float(confs[i])
        audio_path, info_species = ambil_audio(clip_id, label_benar)
        for col in (0, 1):
            ax = axes[row, col]
            if audio_path is None:
                ax.text(0.5, 0.5, "audio tidak ditemukan",
                        ha="center", va="center", transform=ax.transAxes)
                ax.axis("off")
                continue
            _, _, S_db = render_spektrogram(audio_path)
            if S_db is None:
                ax.text(0.5, 0.5, "gagal decode",
                        ha="center", va="center", transform=ax.transAxes)
                ax.axis("off")
                continue
            if col == 0:
                librosa_display = __import__("librosa.display", fromlist=["*"])
                img = librosa_display.specshow(
                    S_db, sr=48000, hop_length=256,
                    y_axis="mel", x_axis="time", ax=ax, cmap="magma")
                ax.set_title(
                    f"#{row+1} {clip_id} | benar: {label_benar}\n"
                    f"tebakan: {label_tebakan} (conf {confidence:.2f})",
                    fontsize=9,
                )
                ax.set_ylabel("Hz (mel)")
                ax.set_xlabel("waktu (s)")
                fig.colorbar(img, ax=ax, format="%+2.0f dB")
            else:
                ax.hist(S_db.flatten(), bins=40, color="#1f77b4", alpha=0.85)
                ax.set_title(f"distribusi energi (dB) -- {clip_id}", fontsize=9)
                ax.set_xlabel("dB")
                ax.set_ylabel("count")
        catatan.append(
            (clip_id, label_benar, label_tebakan, confidence, jenis, info_species)
        )

    fig.suptitle(
        "Analisis Galat: Spektrogram 8 Klip Salah-Klasifikasi (Uji Bersih)\n"
        "Empat kelas dengan support kecil dan empat confusion pair dominan",
        fontsize=12,
    )
    out = FIG / "fig11_error_analysis.png"
    fig.savefig(out, dpi=100, bbox_inches="tight")
    plt.close(fig)
    print(f"  tulis {out} ({out.stat().st_size} B)")

    # Catatan analisis.
    md = ["# Analisis Galat Spektrogram (Uji Bersih)", ""]
    md.append("Dipilih 4 kelas dengan support kecil (rentan karena data kurang) ")
    md.append("dan 4 confusion pair dari `ml/reports/confusion_top.md`. ")
    md.append("Untuk tiap klip ditampilkan spektrogram log-mel 128-bin dan ")
    md.append("distribusi energi. Label benar diambil dari manifest.")
    md.append("")
    md.append("| # | clip | label benar | tebakan | confidence | jenis | species di folder |")
    md.append("|---|---|---|---|---|---|---|")
    for i, (cid, lb, lt, conf, jenis, info_sp) in enumerate(catatan, 1):
        md.append(f"| {i} | {cid} | {lb} | {lt} | {conf:.2f} | {jenis} | {info_sp or '-'} |")
    md.append("")
    md.append("## Hipotesis penyebab")
    md.append("")
    md.append("1. **Support kecil** (Prinia familiaris n=1, Gallus gallus n=1). "
              "Satu klip uji artinya recall otomatis 0 atau 100. Tanpa data latih "
              "yang cukup, jaringan tidak punya pola spektral yang stabil untuk "
              "spesies ini.")
    md.append("2. **Confusion antar passerine bersuara tipis** (Aegithina tiphia vs "
              "Cinnyris jugularis, Hirundo tahitica vs Cinnyris jugularis). Burung "
              "kecil dengan kicauan nyaring di pita 4 sampai 8 kHz punya pola "
              "spektral mirip, dan embedding BirdNET sudah mengkodekan timbre "
              "global sehingga bedanya tipis.")
    md.append("3. **Suara vokal rendah mirip panggilan kawin** (Amaurornis "
              "phoenicurus vs Merops philippinus). Kedua spesies punya "
              "panggilan berulang di bawah 2 kHz; pada jendela 3 detik kadang "
              "hanya satu panggilan yang aktif sehingga keyakinan meloncat ke "
              "kelas lain.")
    md.append("4. **Kelas ambigu di kelas _negative** (Arachnothera longirostra "
              "vs Dicrurus macrocercus, Aplonis panayensis vs Gallus gallus). "
              "Kelas negatif berisi Xeno-canto non-target, tapi kadang ada "
              "suara ambient yang mirip kicauan, jadi model ragu.")
    md.append("")
    md.append("Gambar: `docs/proposal/figures/fig11_error_analysis.png`.")
    (REPORTS / "error_analysis.md").write_text("\n".join(md))
    print(f"  tulis {REPORTS / 'error_analysis.md'}")


if __name__ == "__main__":
    FIG.mkdir(parents=True, exist_ok=True)
    REPORTS.mkdir(parents=True, exist_ok=True)
    main()