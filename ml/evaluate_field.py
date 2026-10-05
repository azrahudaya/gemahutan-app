"""Evaluasi jujur: bersih vs audio lapangan vs tangga degradasi.

Menjawab satu pertanyaan: seberapa jauh performa model jatuh ketika audio tidak
lagi bersih. Tiga kelompok diuji dengan model dan threshold yang sama persis
dengan yang dipakai aplikasi.

  1. bersih        : 218 klip uji Xeno-canto (angka yang sudah dilaporkan)
  2. degradasi     : klip uji yang sama setelah diberi hujan, angin, kota, jarak
  3. lapangan      : rekaman kualitas C/D/E Xeno-canto dan rekaman ponsel
                     iNaturalist, plus kelompok pengecoh untuk mengukur deteksi palsu

Simulasi degradasi bukan rekaman lapangan dan dilaporkan terpisah.

Pakai:
    cd ml && ../.venv/bin/python evaluate_field.py
    cd ml && ../.venv/bin/python evaluate_field.py --maks-jendela 6
"""
import argparse
import csv
import json
import shutil
import subprocess
import sys
from pathlib import Path

import numpy as np

ML_DIR = Path(__file__).resolve().parent
DATA_DIR = ML_DIR / "data"
REPO_DIR = ML_DIR.parent
sys.path.insert(0, str(DATA_DIR))
sys.path.insert(0, str(ML_DIR))
sys.path.insert(0, str(REPO_DIR))  # supaya "from ml.train import MLP" ketemu

REPORTS_DIR = ML_DIR / "reports"
FIGURES_DIR = REPO_DIR / "docs" / "proposal" / "figures"
CHECKPOINT = ML_DIR / "checkpoints" / "best_model.npz"
NORMALIZATION = ML_DIR / "checkpoints" / "normalization.npz"
# Akhiran nama laporan. Dipakai untuk membandingkan dua checkpoint (produksi vs
# hasil latih ulang dengan data lapangan) tanpa saling menimpa.
AKHIRAN = ""
# Klip lapangan berlisensi ND yang sudah dibuang dari korpus sebelum evaluasi ini.
# Catatan tetap, bukan angka yang dihitung ulang.
ND_LAPANGAN_DIBUANG = 50

import extract_embeddings as ee  # noqa: E402

from ml.train import MLP  # noqa: E402

SR = ee.SR
DURATION = ee.DURATION
AMBANG_SENYAP = 0.002  # RMS di bawah ini dianggap latar sunyi


def muat_model():
    label_map = json.loads((ML_DIR / "embeddings" / "label_map.json").read_text())
    inv_map = {v: k for k, v in label_map.items()}
    thresholds = json.loads((REPORTS_DIR / "thresholds.json").read_text())
    # Normalisasi wajib: MLP dilatih pada embedding yang sudah dinormalkan, jadi
    # input mentah harus dikenai mean dan std yang sama supaya hasilnya sahih.
    norm = np.load(NORMALIZATION)
    model = MLP(256, 128, len(label_map))
    model.load(str(CHECKPOINT))
    interp = ee.create_interpreter(ee.get_birdnet_model_path())
    return model, label_map, inv_map, thresholds, interp, norm["mean"], norm["std"]


def tebak(model, X_raw: np.ndarray, mean: np.ndarray, std: np.ndarray,
          jumlah_kelas: int) -> np.ndarray:
    """Prediksi probabilitas dari embedding mentah (dinormalkan dulu)."""
    if not len(X_raw):
        return np.zeros((0, jumlah_kelas), dtype=np.float32)
    return model.forward((X_raw - mean) / std)


def baca_audio(berkas: Path) -> np.ndarray:
    """Baca audio jadi mono 48 kHz.

    Format yang tidak bisa dibaca librosa sendiri (m4a AAC dari ponsel, misalnya)
    didekode dulu lewat ffmpeg ke wav sementara. Tanpa ini, berkas seperti itu
    dilewati diam-diam dan angkanya jadi menyesatkan.
    """
    import librosa

    try:
        y, _ = librosa.load(str(berkas), sr=SR, mono=True)
        return y
    except Exception:
        pass

    if not shutil.which("ffmpeg"):
        raise RuntimeError("ffmpeg tidak ada di PATH")

    import tempfile

    with tempfile.TemporaryDirectory() as tmp:
        tujuan = Path(tmp) / "audio.wav"
        perintah = ["ffmpeg", "-y", "-hide_banner", "-loglevel", "error",
                    "-i", str(berkas), "-ar", str(SR), "-ac", "1", str(tujuan)]
        subprocess.run(perintah, capture_output=True, check=True)
        y, _ = librosa.load(str(tujuan), sr=SR, mono=True)
    return y


def jendela_audio(berkas: Path, maks_jendela: int) -> list[np.ndarray]:
    """Potong audio jadi jendela 3 detik, lewati yang nyaris sunyi."""
    try:
        y = baca_audio(berkas)
    except Exception as exc:
        print(f"    gagal baca {berkas.name}: {str(exc)[:60]}")
        return []

    panjang = int(SR * DURATION)
    langkah = panjang // 2 or panjang
    hasil = []
    for mulai in range(0, max(1, len(y) - panjang + 1), langkah):
        potong = y[mulai:mulai + panjang]
        if len(potong) < panjang:
            potong = np.pad(potong, (0, panjang - len(potong)))
        if float(np.sqrt(np.mean(potong ** 2))) < AMBANG_SENYAP:
            continue
        hasil.append(potong.astype(np.float32))
        if len(hasil) >= maks_jendela:
            break
    return hasil


def embed_folder(interp, berkas_list: list[Path], maks_jendela: int, label: str,
                 verbose: bool = True):
    """Hitung embedding semua jendela dari daftar berkas."""
    fitur, kunci = [], []
    for berkas in berkas_list:
        for jendela in jendela_audio(berkas, maks_jendela):
            fitur.append(ee.extract_birdnet_embedding(interp, jendela))
            kunci.append(berkas.name)
    if not fitur:
        if verbose:
            print(f"  {label}: tidak ada jendela terbaca")
        return np.zeros((0, ee.EMBEDDING_DIM), dtype=np.float32), []
    if verbose:
        print(f"  {label}: {len(fitur)} jendela dari {len(berkas_list)} berkas")
    return np.vstack(fitur).astype(np.float32), kunci


def metrik(y_true: np.ndarray, probs: np.ndarray, inv_map: dict, thresholds: dict,
           kelas_target: list[int]) -> dict:
    """Akurasi top-1, macro F1, dan tingkat deteksi berbasis threshold."""
    preds = np.argmax(probs, axis=1)
    akurasi = float(np.mean(preds == y_true)) if len(y_true) else 0.0

    f1s = []
    for cls in sorted({int(c) for c in y_true if int(c) in kelas_target}):
        benar = y_true == cls
        tebak = preds == cls
        tp = int(np.sum(benar & tebak))
        fp = int(np.sum(~benar & tebak))
        fn = int(np.sum(benar & ~tebak))
        presisi = tp / (tp + fp) if tp + fp else 0.0
        recall = tp / (tp + fn) if tp + fn else 0.0
        f1s.append(2 * presisi * recall / (presisi + recall) if presisi + recall else 0.0)

    # Tingkat deteksi: ada kelas target yang melewati threshold terkalibrasinya.
    ambang = np.array([thresholds.get(inv_map[c], 0.5) for c in range(probs.shape[1])])
    lewat = probs >= ambang
    kelas_target_mask = np.zeros(probs.shape[1], dtype=bool)
    kelas_target_mask[kelas_target] = True
    deteksi = float(np.mean(np.any(lewat[:, kelas_target_mask], axis=1))) if len(y_true) else 0.0

    return {
        "jumlah_jendela": int(len(y_true)),
        "akurasi_top1": round(akurasi, 4),
        "macro_f1": round(float(np.mean(f1s)), 4) if f1s else 0.0,
        "kelas_dinilai": len(f1s),
        "tingkat_deteksi": round(deteksi, 4),
    }


def deteksi_palsu(probs: np.ndarray, inv_map: dict, thresholds: dict,
                  kelas_target: list[int]) -> float:
    """Bagian jendela dari kelompok pengecoh yang salah dikenali sebagai target."""
    if not len(probs):
        return 0.0
    ambang = np.array([thresholds.get(inv_map[c], 0.5) for c in range(probs.shape[1])])
    mask = np.zeros(probs.shape[1], dtype=bool)
    mask[kelas_target] = True
    return round(float(np.mean(np.any((probs >= ambang) & mask, axis=1))), 4)


def lisensi_nd(lic: str | None) -> bool:
    """True kalau lisensi melarang karya turunan, sedangkan pipeline memotong klip."""
    teks = (lic or "").lower()
    return any(tanda in teks for tanda in ("-nd", "/nd", "nd/", "noderiv", "no-deriv"))


def kelompok_lapangan() -> tuple[dict[str, list[Path]], int]:
    """Klip lapangan dikelompokkan, klip berlisensi ND disisihkan dan dihitung."""
    manifest = DATA_DIR / "field" / "manifest.csv"
    if not manifest.exists():
        return {}, 0
    grup: dict[str, list[Path]] = {}
    nd = 0
    with manifest.open() as fh:
        for baris in csv.DictReader(fh):
            if lisensi_nd(baris.get("license", "")):
                nd += 1
                continue
            berkas = DATA_DIR / baris["local_path"]
            if berkas.exists():
                grup.setdefault(baris["group"], []).append(berkas)
    return grup, nd


def buat_grafik(hasil: dict) -> None:
    import matplotlib
    matplotlib.use("Agg")
    import matplotlib.pyplot as plt

    urut = ["bersih", "bersih_tanpa_nd", "kontrol_reencode", "hujan_ringan", "hujan_deras",
            "angin", "kota", "jarak_30m", "jarak_100m", "gabungan_berat"]
    nama = [t for t in urut if t in hasil]
    f1 = [hasil[t]["macro_f1"] for t in nama]
    akurasi = [hasil[t]["akurasi_top1"] for t in nama]
    label = [t.replace("_", " ") for t in nama]

    fig, ax = plt.subplots(figsize=(9, 4.2), dpi=150)
    x = np.arange(len(nama))
    ax.bar(x - 0.2, akurasi, width=0.4, color="#5B7FD4", label="Akurasi top-1")
    ax.bar(x + 0.2, f1, width=0.4, color="#8FB27A", label="Macro F1")
    ax.set_xticks(x)
    ax.set_xticklabels(label, rotation=20, ha="right", fontsize=9)
    ax.set_ylim(0, 1)
    ax.set_ylabel("Nilai")
    ax.set_title("Penurunan performa pada tangga degradasi audio (simulasi)", fontsize=11)
    for i, (a, f) in enumerate(zip(akurasi, f1, strict=True)):
        ax.text(i - 0.2, a + 0.02, f"{a:.2f}", ha="center", fontsize=8)
        ax.text(i + 0.2, f + 0.02, f"{f:.2f}", ha="center", fontsize=8)
    ax.legend(fontsize=9, frameon=False)
    ax.grid(axis="y", alpha=0.25, linewidth=0.6)
    for sisi in ("top", "right"):
        ax.spines[sisi].set_visible(False)
    fig.tight_layout()
    FIGURES_DIR.mkdir(parents=True, exist_ok=True)
    keluaran = FIGURES_DIR / f"fig08_degradasi_audio{AKHIRAN}.png"
    fig.savefig(keluaran)
    plt.close(fig)
    print(f"grafik: {keluaran.relative_to(REPO_DIR)}")


def _tampilkan(berkas: Path) -> str:
    """Jalur relatif ke repo kalau memungkinkan, kalau tidak jalur apa adanya."""
    try:
        return str(berkas.relative_to(REPO_DIR))
    except ValueError:
        return str(berkas)


def tulis_laporan(semua: dict, grup_lapangan_hasil: dict, nd_disisihkan: int = 0,
                  nd_manifest: dict | None = None) -> None:
    REPORTS_DIR.mkdir(parents=True, exist_ok=True)
    urut = ["bersih", "bersih_tanpa_nd", "kontrol_reencode", "hujan_ringan", "hujan_deras",
            "angin", "kota", "jarak_30m", "jarak_100m", "gabungan_berat"]
    kunci = [k for k in urut if k in semua] + [k for k in semua if k not in urut]
    baris = [
        "# Evaluasi Kondisi Audio",
        "",
        f"Model yang dinilai: `{_tampilkan(CHECKPOINT)}`.",
        "Model, threshold, dan cara pemotongan jendela sama dengan yang dipakai aplikasi.",
        "Tangga degradasi adalah simulasi ffmpeg, bukan rekaman lapangan, dan dilaporkan terpisah.",
        "",
        "## Data uji bersih dan tangga degradasi",
        "",
        "| Kondisi | Jendela | Akurasi top-1 | Macro F1 |",
        "|---|---|---|---|",
    ]
    for nama in kunci:
        m = semua[nama]
        baris.append(f"| {nama.replace('_', ' ')} | {m['jumlah_jendela']} | {m['akurasi_top1']:.4f} | {m['macro_f1']:.4f} |")

    if grup_lapangan_hasil:
        baris += [
            "",
            "## Rekaman kondisi lapangan (nyata, berlisensi)",
            "",
            "Kelompok `other` berisi spesies di luar label map, jadi satu-satunya angka",
            "yang bermakna di sana adalah deteksi palsu.",
            "",
            "| Kelompok | Berkas terbaca | Jendela | Akurasi top-1 | Macro F1 | Tingkat deteksi | Deteksi palsu |",
            "|---|---|---|---|---|---|---|",
        ]
        for nama, m in grup_lapangan_hasil.items():
            akurasi = f"{m['akurasi_top1']:.4f}" if "akurasi_top1" in m else "tidak berlaku"
            f1 = f"{m['macro_f1']:.4f}" if "macro_f1" in m else "tidak berlaku"
            deteksi = f"{m['tingkat_deteksi']:.4f}" if "tingkat_deteksi" in m else "tidak berlaku"
            palsu = f"{m['deteksi_palsu']:.4f}" if "deteksi_palsu" in m else "tidak diukur"
            baris.append(
                f"| {nama} | {m.get('berkas_terbaca', m['jumlah_berkas'])} dari {m['jumlah_berkas']} | "
                f"{m['jumlah_jendela']} | "
                f"{akurasi} | {f1} | {deteksi} | {palsu} |"
            )

    baris += [
        "",
        "Catatan pembacaan:",
        "",
        "- Angka bersih adalah baseline yang sudah dilaporkan di eval.md.",
        "- Baris bersih tanpa ND mengulang baseline hanya pada klip uji yang lisensinya",
        "  mengizinkan karya turunan, karena pipeline ini memotong klip dan melatih model.",
    ]
    if nd_manifest:
        baris.append(
            f"- Klip ND di manifest: {nd_manifest.get('total', 0)} dari 1370, "
            f"{nd_manifest.get('di_split_uji', 0)} di antaranya masuk split uji."
        )
    baris.append(f"- Klip lapangan berlisensi ND yang disisihkan: {nd_disisihkan}.")
    baris.append(
        "- Kolom berkas terbaca penting: berkas yang tidak bisa didekode dihitung, "
        "bukan dianggap benar."
    )
    if ND_LAPANGAN_DIBUANG:
        baris.append(
            f"- {ND_LAPANGAN_DIBUANG} klip lapangan ND sudah dibuang dari korpus sebelum "
            "evaluasi ini, karena pipeline memotong klip jadi karya turunan."
        )
    baris += [
        "- Kelompok pengecoh berisi spesies yang tidak dikenal classifier, jadi setiap",
        "  deteksi ke kelas target di kelompok itu dihitung sebagai deteksi palsu.",
        "- Simulasi degradasi mengukur ketahanan terhadap gangguan, bukan pengganti uji lapangan.",
    ]
    (REPORTS_DIR / f"field_metrics{AKHIRAN}.json").write_text(
        json.dumps({"model": str(CHECKPOINT), "degradasi": semua, "lapangan": grup_lapangan_hasil},
                   indent=2, ensure_ascii=False)
    )
    (REPORTS_DIR / f"field_eval{AKHIRAN}.md").write_text("\n".join(baris) + "\n")
    print(f"laporan: {(REPORTS_DIR / f'field_eval{AKHIRAN}.md').relative_to(REPO_DIR)}")


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--maks-jendela", type=int, default=8,
                        help="batas jendela per berkas untuk korpus lapangan")
    parser.add_argument("--lewati-degradasi", action="store_true")
    parser.add_argument("--checkpoint-dir", default=None,
                        help="folder checkpoint yang dinilai (default ml/checkpoints)")
    parser.add_argument("--akhiran", default="",
                        help="akhiran nama laporan, misalnya _aug")
    parser.add_argument("--folder-degradasi", default=None,
                        help="folder berisi subfolder tier (default ml/data/degraded)")
    parser.add_argument("--lewati-lapangan", action="store_true")
    args = parser.parse_args()

    global CHECKPOINT, NORMALIZATION, AKHIRAN
    if args.checkpoint_dir:
        folder = Path(args.checkpoint_dir).resolve()
        CHECKPOINT = folder / "best_model.npz"
        NORMALIZATION = folder / "normalization.npz"
    AKHIRAN = args.akhiran
    print(f"checkpoint: {CHECKPOINT}")
    if not CHECKPOINT.exists():
        print(f"checkpoint tidak ada: {CHECKPOINT}")
        return 1

    model, label_map, inv_map, thresholds, interp, mean, std = muat_model()
    kelas_target = [c for c, nama in inv_map.items() if not nama.startswith("_")]
    semua: dict[str, dict] = {}

    # 1. Baseline bersih dari embedding yang sudah ada, jadi tidak dihitung ulang.
    emb = np.load(ML_DIR / "embeddings" / "embeddings.npy")
    label = np.load(ML_DIR / "embeddings" / "labels.npy")
    splits = json.loads((DATA_DIR / "splits.json").read_text())
    posisi = {cid: i for i, cid in enumerate(json.loads((ML_DIR / "embeddings" / "clip_ids.json").read_text()))}
    idx_uji = [posisi[c] for c in splits["test"] if c in posisi]
    X_uji, y_uji = emb[idx_uji], label[idx_uji]
    semua["bersih"] = metrik(y_uji, tebak(model, X_uji, mean, std, len(label_map)),
                             inv_map, thresholds, kelas_target)
    print("  bersih:", semua["bersih"])

    # 1b. Baseline yang hanya memakai klip uji berlisensi boleh dipakai (tanpa ND).
    with (DATA_DIR / "manifest.csv").open() as fh:
        lisensi_klip = {b["clip_id"]: b.get("license", "") for b in csv.DictReader(fh)}
    id_uji_nd = {c for c in splits["test"] if lisensi_nd(lisensi_klip.get(c, ""))}
    idx_uji_bersih = [posisi[c] for c in splits["test"] if c in posisi and c not in id_uji_nd]
    X_bersih, y_bersih = emb[idx_uji_bersih], label[idx_uji_bersih]
    semua["bersih_tanpa_nd"] = metrik(
        y_bersih, tebak(model, X_bersih, mean, std, len(label_map)),
        inv_map, thresholds, kelas_target)
    print("  bersih tanpa ND:", semua["bersih_tanpa_nd"])
    nd_manifest = {
        "total": sum(1 for v in lisensi_klip.values() if lisensi_nd(v)),
        "di_split_uji": len(id_uji_nd),
    }

    # 2. Tangga degradasi.
    if not args.lewati_degradasi:
        folder_degradasi = (Path(args.folder_degradasi).resolve()
                             if args.folder_degradasi
                             else DATA_DIR / "degraded")
        if folder_degradasi.exists():
            print("tangga degradasi:")
            for tier in sorted(p.name for p in folder_degradasi.iterdir() if p.is_dir()):
                berkas = sorted((folder_degradasi / tier).glob("*.wav"))
                if not berkas:
                    continue
                # Tiap berkas diproses satu per satu supaya label selalu sejajar
                # dengan jendela yang benar-benar terbaca (berkas sunyi dilewati).
                X_bagian, y_bagian = [], []
                for berkas_satu in berkas:
                    if berkas_satu.stem not in posisi:
                        continue
                    fitur_satu, _ = embed_folder(interp, [berkas_satu], 1, "", verbose=False)
                    if not len(fitur_satu):
                        continue
                    X_bagian.append(fitur_satu)
                    y_bagian.append(np.full(len(fitur_satu), label[posisi[berkas_satu.stem]], dtype=int))
                X = np.vstack(X_bagian) if X_bagian else np.zeros((0, ee.EMBEDDING_DIM), dtype=np.float32)
                y = np.concatenate(y_bagian) if y_bagian else np.array([], dtype=int)
                semua[tier] = metrik(y, tebak(model, X, mean, std, len(label_map)),
                                     inv_map, thresholds, kelas_target)
                semua[tier]["jumlah_berkas"] = len(berkas)
                print(f"  {tier}: {semua[tier]}")

    # 3. Korpus lapangan nyata: tiap berkas punya spesies sebenarnya dari manifest.
    grup_hasil: dict = {}
    grup: dict = {}
    nd_lapangan: int = 0
    if not args.lewati_lapangan:
        grup, nd_lapangan = kelompok_lapangan()
    if nd_lapangan:
        print(f"korpus lapangan: {nd_lapangan} klip ND disisihkan (karya turunan tidak boleh)")
    if grup:
        print("korpus lapangan:")
        for nama, berkas in sorted(grup.items()):
            X_bagian, y_bagian = [], []
            terbaca = 0
            for berkas_satu in berkas:
                kelas = label_map.get(berkas_satu.parent.name.replace("_", " "), -1)
                # Kelompok pengecoh sengaja di luar label map: audionya tetap
                # dihitung supaya deteksi palsu bisa diukur.
                if kelas < 0 and nama != "other":
                    continue
                fitur_satu, _ = embed_folder(interp, [berkas_satu], args.maks_jendela, "", verbose=False)
                if not len(fitur_satu):
                    continue
                terbaca += 1
                X_bagian.append(fitur_satu)
                if kelas >= 0:
                    y_bagian.append(np.full(len(fitur_satu), kelas, dtype=int))

            X = np.vstack(X_bagian) if X_bagian else np.zeros((0, ee.EMBEDDING_DIM), dtype=np.float32)
            y = np.concatenate(y_bagian) if y_bagian else np.array([], dtype=int)
            probs = tebak(model, X, mean, std, len(label_map))

            if nama == "other":
                # Semua spesies di kelompok ini di luar label map, jadi setiap
                # deteksi ke kelas target dihitung salah.
                grup_hasil[nama] = {
                    "jumlah_berkas": len(berkas),
                    "berkas_terbaca": terbaca,
                    "jumlah_jendela": int(len(X)),
                    "deteksi_palsu": deteksi_palsu(probs, inv_map, thresholds, kelas_target),
                }
            else:
                m = metrik(y, probs, inv_map, thresholds, kelas_target)
                m["jumlah_berkas"] = len(berkas)
                m["berkas_terbaca"] = terbaca
                grup_hasil[nama] = m
            print(f"  {nama}: {grup_hasil[nama]}")

    tulis_laporan(semua, grup_hasil, nd_lapangan, nd_manifest)
    if not args.lewati_degradasi:
        buat_grafik(semua)
    return 0


if __name__ == "__main__":
    sys.exit(main())
