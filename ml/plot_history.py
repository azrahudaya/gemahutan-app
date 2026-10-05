"""Kurva training: latih ulang model dengan seed 42, 100 epoch, simpan
history per-epoch ke ml/runs/<id>/history.json dan render kurva
ke docs/proposal/figures/fig12_train_history.png (2 subplot: loss
dan accuracy).

100 epoch cukup untuk menggambarkan tren (model produksi dilatih 300 epoch
di train.py; lihat ml/reports/eval.md untuk trade-off).
"""
import json
import sys
from datetime import datetime
from pathlib import Path

import numpy as np

ML_DIR = Path(__file__).resolve().parent
REPO_DIR = ML_DIR.parent
sys.path.insert(0, str(REPO_DIR))
sys.path.insert(0, str(ML_DIR))

from ml.train import MLP, accuracy, cross_entropy_loss  # noqa: E402

EMB_DIR = ML_DIR / "embeddings"
SPLITS = ML_DIR / "data" / "splits.json"
RUNS = ML_DIR / "runs"
FIG = REPO_DIR / "docs" / "proposal" / "figures"


def muat_data():
    emb = np.load(EMB_DIR / "embeddings.npy")
    labels = np.load(EMB_DIR / "labels.npy")
    with open(EMB_DIR / "clip_ids.json") as f:
        ids = json.load(f)
    with open(SPLITS) as f:
        sp = json.load(f)
    with open(EMB_DIR / "label_map.json") as f:
        label_map = json.load(f)
    cid_idx = {c: i for i, c in enumerate(ids)}

    def get(name):
        idx = [cid_idx[c] for c in sp[name] if c in cid_idx]
        return emb[idx], labels[idx]

    X_tr, y_tr = get("train")
    X_va, y_va = get("val")
    X_te, y_te = get("test")
    mean = X_tr.mean(axis=0)
    std = X_tr.std(axis=0) + 1e-8
    X_tr = (X_tr - mean) / std
    X_va = (X_va - mean) / std
    X_te = (X_te - mean) / std
    return X_tr, y_tr, X_va, y_va, X_te, y_te, label_map, mean, std


def main():
    import matplotlib

    matplotlib.use("Agg")
    import matplotlib.pyplot as plt

    np.random.seed(42)
    X_tr, y_tr, X_va, y_va, X_te, y_te, label_map, mean, std = muat_data()
    n_classes = len(label_map)
    model = MLP(1024, 256, n_classes, lr=0.001)

    run_id = datetime.now().strftime("%Y%m%d-%H%M%S")
    run_dir = RUNS / run_id
    run_dir.mkdir(parents=True, exist_ok=True)

    epochs = 100
    batch = 64
    history = []
    best_va = 0
    print(f"Training {epochs} epoch (seed 42) ...")
    for ep in range(epochs):
        perm = np.random.permutation(len(X_tr))
        Xs, ys = X_tr[perm], y_tr[perm]
        ep_loss = 0
        n_bat = 0
        for i in range(0, len(Xs), batch):
            Xb = Xs[i:i + batch]
            yb = ys[i:i + batch]
            y_onehot = np.zeros((len(yb), n_classes), dtype=np.float32)
            y_onehot[np.arange(len(yb)), yb] = 1
            probs = model.forward(Xb)
            loss = cross_entropy_loss(probs, yb)
            model.backward(Xb, y_onehot)
            ep_loss += loss
            n_bat += 1
        train_loss = ep_loss / max(n_bat, 1)
        train_preds = model.predict(X_tr)
        train_acc = accuracy(train_preds, y_tr)
        val_preds = model.predict(X_va)
        val_acc = accuracy(val_preds, y_va)
        if val_acc > best_va:
            best_va = val_acc
        history.append({
            "epoch": ep,
            "loss": float(train_loss),
            "train_acc": float(train_acc),
            "val_acc": float(val_acc),
        })
        if (ep + 1) % 10 == 0:
            print(f"  ep {ep+1}: loss={train_loss:.3f} tr={train_acc:.3f} va={val_acc:.3f}")

    with open(run_dir / "history.json", "w") as f:
        json.dump(history, f, indent=2)
    print(f"  tulis history -> {run_dir / 'history.json'}")

    fig, axes = plt.subplots(1, 2, figsize=(12, 5), dpi=130)
    epochs_x = [h["epoch"] + 1 for h in history]
    losses = [h["loss"] for h in history]
    train_accs = [h["train_acc"] for h in history]
    val_accs = [h["val_acc"] for h in history]
    axes[0].plot(epochs_x, losses, color="#1f77b4", lw=1.4)
    axes[0].set_xlabel("Epoch")
    axes[0].set_ylabel("Train loss (cross-entropy)")
    axes[0].set_title("Kurva Loss Pelatihan")
    axes[0].grid(True, alpha=0.3)
    axes[1].plot(epochs_x, train_accs, label="Train acc", color="#1f77b4", lw=1.4)
    axes[1].plot(epochs_x, val_accs, label="Val acc", color="#d62728", lw=1.4)
    axes[1].set_xlabel("Epoch")
    axes[1].set_ylabel("Akurasi")
    axes[1].set_title("Kurva Akurasi Train vs Val")
    axes[1].legend()
    axes[1].grid(True, alpha=0.3)
    fig.suptitle(
        f"Kurva Pelatihan (seed 42, {epochs} epoch, hidden 256, lr 0,001)\n"
        f"Best val_acc = {best_va:.4f}",
        fontsize=12,
    )
    plt.tight_layout(rect=[0, 0, 1, 0.94])
    out = FIG / "fig12_train_history.png"
    fig.savefig(out, dpi=130, bbox_inches="tight")
    plt.close(fig)
    print(f"  tulis {out} ({out.stat().st_size} B)")


if __name__ == "__main__":
    RUNS.mkdir(parents=True, exist_ok=True)
    FIG.mkdir(parents=True, exist_ok=True)
    main()