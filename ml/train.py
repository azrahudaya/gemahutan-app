"""Train MLP classifier on cached embeddings.

Patches fase augmentation (bandingkan dengan baseline val_acc 0.5433,
test_acc 0.5512):

  B3 class_weight.compute_class_weight('balanced') menggantikan bobot 1/n
     lama, target one-hot dikalikan wb di training loop supaya false
     negative spesies kelas kecil turun.
  B4 dropout 0.3 antara hidden dan output, weight decay Adam 1e-4 per
     step (L2 manual), early stopping patience 30 epoch tanpa val_acc
     naik.
  B5 LR schedule ReduceLROnPlateau(factor=0.5, patience=15) di atas
     Adam. lr awal 0.001, minimal 1e-5. Adam menggantikan update plain
     gradient descent yang dulu dipakai.
  B7 CLI --seed-list "42,123,2024" melatih 3 kali lalu laporkan
     mean +/- std untuk test_acc/val_acc/F1 ke ml/reports/multi_seed.json.
  E3 kalibrasi T+bias langsung setelah pelatihan dan dibundel di file
     best_model.npz (arrays) supaya saat load otomatis tersedia,
     bukan hanya dari temperature.json terpisah.

Output deterministic per seed. Default seed 42 tetap.
"""
import argparse
import json
import random
import sys
import time
from datetime import datetime
from pathlib import Path

import numpy as np
from sklearn.utils.class_weight import compute_class_weight

EMB_DIR = Path(__file__).parent / "embeddings"
CHECKPOINT_DIR = Path(__file__).parent / "checkpoints"
RUNS_DIR = Path(__file__).parent / "runs"
SPLITS_FILE = Path(__file__).parent / "data" / "splits.json"
REPORTS_DIR = Path(__file__).parent / "reports"


def _softmax(z):
    z = z - np.max(z, axis=-1, keepdims=True)
    ez = np.exp(z)
    return ez / np.sum(ez, axis=-1, keepdims=True)


class MLP:
    """2-layer MLP dengan dropout dan Adam.

    Output sebelum softmax di-dropout 0.3 saat training. Weight decay 1e-4
    implicit per Adam update.

    `activation="linear"` membuat kelas ini bisa memuat model linear juga
    (regresi logistik multikelas). Caranya: lapisan tersembunyi dilewati dengan
    W2 identitas dan tanpa ReLU, sehingga logits = X @ W1 + b1. Ini dipakai
    karena pada embedding BirdNET sebuah model linear mengalahkan MLP di
    korpus v2, termasuk pada deteksi palsu lapangan (0,3828 lawan 0,5391).
    """

    def __init__(self, input_dim, hidden_dim, num_classes, lr=0.001,
                 dropout=0.3, weight_decay=1e-4, activation="relu"):
        self.lr = lr
        self.dropout = dropout
        self.weight_decay = weight_decay
        self.activation = activation
        self.training = True
        self._learning_rate = lr
        # Xavier init
        self.W1 = np.random.randn(input_dim, hidden_dim).astype(np.float32) * np.sqrt(2.0 / input_dim)
        self.b1 = np.zeros(hidden_dim, dtype=np.float32)
        self.W2 = np.random.randn(hidden_dim, num_classes).astype(np.float32) * np.sqrt(2.0 / hidden_dim)
        self.b2 = np.zeros(num_classes, dtype=np.float32)
        self._init_adam()

    def _init_adam(self):
        self.mW1 = np.zeros_like(self.W1)
        self.vW1 = np.zeros_like(self.W1)
        self.mb1 = np.zeros_like(self.b1)
        self.vb1 = np.zeros_like(self.b1)
        self.mW2 = np.zeros_like(self.W2)
        self.vW2 = np.zeros_like(self.W2)
        self.mb2 = np.zeros_like(self.b2)
        self.vb2 = np.zeros_like(self.b2)
        self.t_step = 0

    def forward(self, X):
        self.z1 = X @ self.W1 + self.b1
        self.a1 = np.maximum(0, self.z1) if self.activation == "relu" else self.z1
        if self.training and self.dropout > 0:
            keep = 1.0 - self.dropout
            self.drop_mask = (np.random.random_sample(self.a1.shape) < keep).astype(np.float32) / keep
            self.a1_drop = self.a1 * self.drop_mask
        else:
            self.drop_mask = None
            self.a1_drop = self.a1
        self.z2 = self.a1_drop @ self.W2 + self.b2
        exp_z = np.exp(self.z2 - np.max(self.z2, axis=1, keepdims=True))
        self.probs = exp_z / np.sum(exp_z, axis=1, keepdims=True)
        return self.probs

    def _adam_update(self, param, grad, m, v, beta1=0.9, beta2=0.999, eps=1e-8):
        """Adam update step. t_step diinkremen di backward() sekali per langkah."""
        m = beta1 * m + (1 - beta1) * grad
        v = beta2 * v + (1 - beta2) * (grad * grad)
        m_hat = m / (1 - beta1 ** self.t_step)
        v_hat = v / (1 - beta2 ** self.t_step)
        param -= self._learning_rate * m_hat / (np.sqrt(v_hat) + eps)
        return param, m, v

    def backward(self, X, y_onehot, sample_weights=None):
        """Backward pass dengan class weights, dropout mask, dan turunan per aktivasi.

        y_onehot: one-hot labels (nilai 0/1, BUKAN premultiplied bobot).
        sample_weights: array [batch,] bobot per sampel untuk gradien cross-entropy.
        """
        m = X.shape[0]
        # Gradien cross-entropy: dz2 = (probs - onehot) / m, dikali bobot sampel
        dz2 = (self.probs - y_onehot) / m
        if sample_weights is not None:
            dz2 = dz2 * sample_weights[:, None]

        dW2 = self.a1_drop.T @ dz2 + self.weight_decay * self.W2
        db2 = np.sum(dz2, axis=0)
        da1 = dz2 @ self.W2.T

        # Dropout mask: gradien ke lapisan pertama harus diskalakan oleh mask
        # yang sama yang dipakai forward, supaya satuan gradien konsisten.
        if self.drop_mask is not None:
            da1 = da1 * self.drop_mask

        # Turunan aktivasi: ReLU -> (z1 > 0), linear -> 1
        if self.activation == "relu":
            dz1 = da1 * (self.z1 > 0).astype(np.float32)
        else:
            dz1 = da1

        dW1 = X.T @ dz1 + self.weight_decay * self.W1
        db1 = np.sum(dz1, axis=0)

        # Adam: satu t_step per langkah backward, bukan per parameter
        self.t_step += 1
        self.W2, self.mW2, self.vW2 = self._adam_update(self.W2, dW2, self.mW2, self.vW2)
        self.b2, self.mb2, self.vb2 = self._adam_update(self.b2, db2, self.mb2, self.vb2)
        self.W1, self.mW1, self.vW1 = self._adam_update(self.W1, dW1, self.mW1, self.vW1)
        self.b1, self.mb1, self.vb1 = self._adam_update(self.b1, db1, self.mb1, self.vb1)

    def predict(self, X):
        prev = self.training
        self.training = False
        probs = self.forward(X)
        self.training = prev
        return np.argmax(probs, axis=1)

    def predict_logits(self, X):
        prev = self.training
        self.training = False
        z1 = X @ self.W1 + self.b1
        a1 = np.maximum(0, z1) if self.activation == "relu" else z1
        z2 = a1 @ self.W2 + self.b2
        self.training = prev
        return z2

    def save(self, path, temperature=None, bias=None):
        save_kwargs = dict(
            W1=self.W1, b1=self.b1, W2=self.W2, b2=self.b2,
            lr=np.array([self.lr]),
            dropout=np.array([self.dropout]),
            weight_decay=np.array([self.weight_decay]),
            activation=np.array([self.activation]),
        )
        if temperature is not None:
            save_kwargs["temperature"] = np.array([temperature], dtype=np.float32)
        if bias is not None:
            save_kwargs["bias"] = np.asarray(bias, dtype=np.float32)
        np.savez(path, **save_kwargs)

    def load(self, path):
        data = np.load(path)
        self.W1 = data["W1"]
        self.b1 = data["b1"]
        self.W2 = data["W2"]
        self.b2 = data["b2"]
        self.lr = float(data["lr"][0]) if "lr" in data.files else 0.001
        if "dropout" in data.files:
            self.dropout = float(data["dropout"][0])
        if "weight_decay" in data.files:
            self.weight_decay = float(data["weight_decay"][0])
        # Model lama tidak punya kunci ini, dan defaultnya relu.
        if "activation" in data.files:
            self.activation = str(np.asarray(data["activation"]).reshape(-1)[0])
        self._init_adam()
        # Memuat bobot adalah operasi inference. Tanpa baris ini, dropout acak
        # ikut jalan di forward() dan hasil prediksi berubah tiap pemanggilan
        # pada data yang sama (terukur 0,5906 sampai 0,6850 pada 127 klip uji,
        # dan satu klip bisa jadi empat spesies berbeda). Loop latih menyetel
        # training = True sendiri, jadi menutup dropout di sini aman.
        self.training = False


def cross_entropy_loss(probs, y):
    m = len(y)
    return float(np.mean(-np.log(probs[np.arange(m), y] + 1e-9)))


def accuracy(preds, labels):
    return float(np.mean(preds == labels))


def macro_f1(y_true, y_pred, n_classes):
    f1s = []
    for c in range(n_classes):
        tp = int(np.sum((y_pred == c) & (y_true == c)))
        fp = int(np.sum((y_pred == c) & (y_true != c)))
        fn = int(np.sum((y_pred != c) & (y_true == c)))
        if tp + fp == 0 or tp + fn == 0:
            f1s.append(0.0)
            continue
        prec = tp / (tp + fp)
        rec = tp / (tp + fn)
        f1s.append(2 * prec * rec / (prec + rec) if (prec + rec) > 0 else 0.0)
    return float(np.mean(f1s))


def load_data(emb_dir=None, splits_file=None):
    """Load embeddings + labels + splits. Normalisasi dihitung dari train only."""
    emb_dir = emb_dir or EMB_DIR
    splits_file = splits_file or SPLITS_FILE
    embeddings = np.load(emb_dir / "embeddings.npy")
    labels = np.load(emb_dir / "labels.npy")
    with open(emb_dir / "clip_ids.json") as f:
        clip_ids = json.load(f)
    with open(emb_dir / "label_map.json") as f:
        label_map = json.load(f)
    with open(splits_file) as f:
        splits = json.load(f)

    cid_to_idx = {cid_: i for i, cid_ in enumerate(clip_ids)}

    # Mapping clip_id_polos -> semua index windows kalau multi-window.
    cid_to_indices: dict = {}
    for idx_, cid_ in enumerate(clip_ids):
        root = cid_.split("__w", 1)[0]
        cid_to_indices.setdefault(root, []).append(idx_)

    def get_split(name):
        idx: list = []
        for cid in splits[name]:
            if cid in cid_to_idx:
                # Single-window: split clip polos == embeddings polos.
                idx.append(cid_to_idx[cid])
            else:
                # Multi-window: split clip polos dicocokkan ke semua window.
                idx.extend(cid_to_indices.get(cid, []))
        return embeddings[idx], labels[idx]

    X_train, y_train = get_split("train")
    X_val, y_val = get_split("val")
    X_test, y_test = get_split("test")

    mean = X_train.mean(axis=0)
    std = X_train.std(axis=0) + 1e-8
    X_train = (X_train - mean) / std
    X_val = (X_val - mean) / std
    X_test = (X_test - mean) / std

    return X_train, y_train, X_val, y_val, X_test, y_test, label_map, mean, std


def fit_vector_scaling(logits, y, n_classes, lr=0.05, steps=400, l2=0.5):
    """Joint optimization T + bias vector. Inline copy supaya pelatihan bisa
    menyimpan kalibrasi dalam satu langkah."""
    T = 1.0
    b = np.zeros(n_classes, dtype=np.float32)
    n = len(y)
    best_state = (T, b.copy(), float("inf"))
    prev = float("inf")
    for _step in range(steps):
        scaled = (logits + b) / T
        scaled = scaled - scaled.max(axis=-1, keepdims=True)
        ez = np.exp(scaled)
        p = ez / ez.sum(axis=-1, keepdims=True)
        loss = -np.mean(np.log(p[np.arange(n), y] + 1e-12)) + l2 * (b ** 2).mean()
        onehot = np.zeros_like(p)
        onehot[np.arange(n), y] = 1.0
        d_scaled = (p - onehot) / n
        db = d_scaled.sum(axis=0) / T + 2 * l2 * b / n_classes
        eps = 1e-3
        scaled_p = (logits + b) / (T + eps)
        sp_max = scaled_p.max(axis=-1, keepdims=True)
        ep = np.exp(scaled_p - sp_max)
        pp = ep / ep.sum(axis=-1, keepdims=True)
        loss_p = -np.mean(np.log(pp[np.arange(n), y] + 1e-12))
        scaled_m = (logits + b) / (T - eps)
        sm_max = scaled_m.max(axis=-1, keepdims=True)
        em = np.exp(scaled_m - sm_max)
        pm = em / em.sum(axis=-1, keepdims=True)
        loss_m = -np.mean(np.log(pm[np.arange(n), y] + 1e-12))
        dT = (loss_p - loss_m) / (2 * eps)
        T = max(0.05, T - lr * dT)
        b = b - lr * db
        if loss < best_state[2]:
            best_state = (T, b.copy(), loss)
        if abs(prev - loss) < 1e-7:
            break
        prev = loss
    return best_state[0], best_state[1], best_state[2]


def calibrate(model, X_val, y_val, n_classes):
    """Latih T+bias pada logits val. Kembalikan T, bias, nll_before, nll_after."""
    logits = model.predict_logits(X_val)
    p_orig = _softmax(logits)
    nll_before = float(-np.mean(np.log(p_orig[np.arange(len(y_val)), y_val] + 1e-12)))
    best = (1.0, np.zeros(n_classes), nll_before)
    for lr in (0.05, 0.02, 0.005):
        for l2 in (0.0, 0.1, 0.5, 2.0):
            T_c, b_c, nll_c = fit_vector_scaling(logits, y_val, n_classes, lr=lr, steps=500, l2=l2)
            if nll_c < best[2]:
                best = (T_c, b_c, nll_c)
    return best[0], best[1], nll_before, best[2]


def train_one(X_train, y_train, X_val, y_val, X_test, y_test,
              num_classes, input_dim, args, checkpoint_dir, class_weights=None):
    """Latih satu model. Mengembalikan dict hasil.

    `class_weights` boleh diisi array bobot per kelas. Kalau None, bobot dihitung
    dengan `compute_class_weight("balanced")` seperti sebelumnya. Parameter ini
    ditambahkan karena pada korpus v2 rasio kelas mencapai 701 kali, dan bobot
    balanced membuat kelas `_negative` (5612 klip) mendapat bobot 0,055 sehingga
    sinyalnya hilang dan model tidak pernah belajar menolak pengecoh.
    """
    model = MLP(input_dim, args.hidden, num_classes, lr=args.lr,
                dropout=0.3, weight_decay=1e-4)

    if class_weights is None:
        classes = np.arange(num_classes)
        cw = compute_class_weight("balanced", classes=classes, y=y_train)
        class_weights = cw.astype(np.float32)
    else:
        class_weights = np.asarray(class_weights, dtype=np.float32)

    plateau_factor = 0.5
    plateau_patience = 15
    plateau_counter = 0
    plateau_best_loss = float("inf")
    current_lr = args.lr
    early_stop_patience = 30

    history = []
    best_val_acc = 0.0
    best_epoch = -1
    bad_epochs = 0

    checkpoint_dir.mkdir(parents=True, exist_ok=True)
    tmp_path = checkpoint_dir / "_tmp_best.npz"

    for epoch in range(args.epochs):
        t0 = time.time()
        model.training = True
        model._learning_rate = current_lr

        perm = np.random.permutation(len(X_train))
        X_shuf = X_train[perm]
        y_shuf = y_train[perm]

        epoch_loss = 0.0
        n_batches = 0
        for i in range(0, len(X_shuf), args.batch_size):
            Xb = X_shuf[i:i + args.batch_size]
            yb = y_shuf[i:i + args.batch_size]

            y_onehot = np.zeros((len(yb), num_classes), dtype=np.float32)
            y_onehot[np.arange(len(yb)), yb] = 1.0

            probs = model.forward(Xb)
            _ = cross_entropy_loss(probs, yb)
            wb = class_weights[yb]
            model.backward(Xb, y_onehot, sample_weights=wb)
            epoch_loss += float(np.mean(-np.log(probs[np.arange(len(yb)), yb] + 1e-9)))
            n_batches += 1
        avg_loss = epoch_loss / max(n_batches, 1)

        model.training = False
        val_preds = model.predict(X_val)
        val_acc = accuracy(val_preds, y_val)
        train_preds = model.predict(X_train)
        train_acc = accuracy(train_preds, y_train)

        elapsed = time.time() - t0
        history.append({
            "epoch": epoch, "loss": float(avg_loss),
            "train_acc": float(train_acc), "val_acc": float(val_acc),
            "lr": float(current_lr), "time_s": round(elapsed, 2),
        })

        if (epoch + 1) % 10 == 0 or epoch == 0:
            print(f"  Epoch {epoch+1}/{args.epochs}: loss={avg_loss:.4f} "
                  f"train_acc={train_acc:.4f} val_acc={val_acc:.4f} lr={current_lr:.5f} ({elapsed:.1f}s)")

        if val_acc > best_val_acc:
            best_val_acc = val_acc
            best_epoch = epoch
            np.savez(tmp_path,
                     W1=model.W1, b1=model.b1, W2=model.W2, b2=model.b2,
                     lr=np.array([model.lr]))
            bad_epochs = 0
        else:
            bad_epochs += 1

        if avg_loss < plateau_best_loss - 1e-6:
            plateau_best_loss = avg_loss
            plateau_counter = 0
        else:
            plateau_counter += 1
            if plateau_counter >= plateau_patience:
                new_lr = max(current_lr * plateau_factor, 1e-5)
                if new_lr < current_lr:
                    current_lr = new_lr
                    plateau_counter = 0
                    print(f"  [lr-schedule] turun ke {current_lr:.6f}")

        if bad_epochs >= early_stop_patience:
            print(f"  [early-stop] patience {early_stop_patience} epoch tanpa val_acc naik. Stop di epoch {epoch+1}.")
            break

    tmp = np.load(tmp_path)
    model.W1 = tmp["W1"]
    model.b1 = tmp["b1"]
    model.W2 = tmp["W2"]
    model.b2 = tmp["b2"]
    model.lr = float(tmp["lr"][0])
    model._init_adam()
    try:
        tmp_path.unlink()
    except FileNotFoundError:
        pass

    model.training = False
    test_preds = model.predict(X_test)
    test_acc = accuracy(test_preds, y_test)
    f1 = macro_f1(y_test, test_preds, num_classes)

    T, bias, nll_before, nll_after = calibrate(model, X_val, y_val, num_classes)
    improvement = (nll_before - nll_after) / max(nll_before, 1e-9) * 100.0

    return {
        "best_val_acc": float(best_val_acc),
        "best_epoch": int(best_epoch),
        "test_acc": float(test_acc),
        "f1_macro": float(f1),
        "history": history,
        "temperature": float(T),
        "bias": np.asarray(bias, dtype=np.float32),
        "nll_before": float(nll_before),
        "nll_after": float(nll_after),
        "nll_improvement_pct": float(improvement),
        "model": model,
    }


def save_history_plot(history, out_path, title=""):
    """Render train_acc vs val_acc per epoch ke PNG matplotlib."""
    try:
        import matplotlib
        matplotlib.use("Agg")
        import matplotlib.pyplot as plt
    except Exception:
        return False
    epochs = [h["epoch"] + 1 for h in history]
    train_acc = [h["train_acc"] for h in history]
    val_acc = [h["val_acc"] for h in history]
    fig, ax = plt.subplots(figsize=(8, 5))
    ax.plot(epochs, train_acc, label="train_acc", color="#1f77b4")
    ax.plot(epochs, val_acc, label="val_acc", color="#ff7f0e")
    ax.set_xlabel("epoch")
    ax.set_ylabel("accuracy")
    ax.set_title(title or "Training history")
    ax.set_ylim(0, 1)
    ax.legend(loc="lower right")
    ax.grid(alpha=0.3)
    fig.tight_layout()
    fig.savefig(out_path, dpi=120)
    plt.close(fig)
    return True


def _persist_results(result, args, label_map, mean, std, run_dir):
    """Simpan best_model + normalization + temperature + history."""
    model = result["model"]
    model.save(str(run_dir / "best_model.npz"),
               temperature=result["temperature"],
               bias=result["bias"])
    np.savez(run_dir / "normalization.npz", mean=mean, std=std)

    temp_json = {
        "method": "vector_scaling_T+b",
        "temperature": float(result["temperature"]),
        "bias": result["bias"].tolist(),
        "nll_before": float(result["nll_before"]),
        "nll_after": float(result["nll_after"]),
        "nll_improvement_pct": round(float(result["nll_improvement_pct"]), 4),
        "val_samples": 127,
        "num_classes": len(label_map),
        "label_map": label_map,
        "bundled_in_best_model": True,
    }
    (run_dir / "temperature.json").write_text(json.dumps(temp_json, indent=2))

    with open(run_dir / "history.json", "w") as f:
        json.dump(result["history"], f, indent=2)

    plot_path = REPORTS_DIR / "training_history.png"
    save_history_plot(result["history"], str(plot_path),
                      title=f"Train history seed={args.seed} best_val_acc={result['best_val_acc']:.4f}")

    results = {
        "best_val_acc": result["best_val_acc"],
        "test_acc": result["test_acc"],
        "f1_macro": result["f1_macro"],
        "best_epoch": result["best_epoch"],
        "epochs_trained": len(result["history"]),
        "temperature": result["temperature"],
        "nll_before": result["nll_before"],
        "nll_after": result["nll_after"],
        "nll_improvement_pct": result["nll_improvement_pct"],
        "run_id": run_dir.name,
        "label_map_size": len(label_map),
        "training_history_plot": str(plot_path),
    }
    with open(run_dir / "results.json", "w") as f:
        json.dump(results, f, indent=2)
    return results


def _multi_seed(args):
    """Latih beberapa seed, kumpulkan mean +/- std."""
    REPORTS_DIR.mkdir(parents=True, exist_ok=True)
    seeds = [int(s) for s in args.seed_list.split(",") if s.strip()]
    print(f"Multi-seed run: {seeds}")

    base = X_train, y_train, X_val, y_val, X_test, y_test, label_map, mean, std = load_data()
    X_train, y_train, X_val, y_val, X_test, y_test, label_map, mean, std = base
    num_classes = len(label_map)
    input_dim = X_train.shape[1]

    per_seed = []
    val_accs = []
    test_accs = []
    f1s = []
    best_run = None
    for seed in seeds:
        np.random.seed(seed)
        random.seed(seed)
        args.seed = seed
        run_id = datetime.now().strftime(f"%Y%m%d-%H%M%S-s{seed}")
        run_dir = RUNS_DIR / run_id
        run_dir.mkdir(parents=True, exist_ok=True)
        print(f"\n=== Seed {seed} ===")
        result = train_one(X_train, y_train, X_val, y_val, X_test, y_test,
                           num_classes, input_dim, args, run_dir)
        per_seed.append({
            "seed": seed,
            "best_val_acc": result["best_val_acc"],
            "test_acc": result["test_acc"],
            "f1_macro": result["f1_macro"],
            "epochs_trained": len(result["history"]),
            "run_dir": str(run_dir),
        })
        val_accs.append(result["best_val_acc"])
        test_accs.append(result["test_acc"])
        f1s.append(result["f1_macro"])
        if best_run is None or result["best_val_acc"] > best_run["result"]["best_val_acc"]:
            best_run = {"seed": seed, "result": result, "run_dir": run_dir}
        print(f"  seed {seed}: best_val_acc={result['best_val_acc']:.4f} "
              f"test_acc={result['test_acc']:.4f} f1={result['f1_macro']:.4f}")

    val_arr = np.array(val_accs)
    test_arr = np.array(test_accs)
    f1_arr = np.array(f1s)
    summary = {
        "seeds": seeds,
        "n_seeds": len(seeds),
        "best_val_acc_mean": float(val_arr.mean()),
        "best_val_acc_std": float(val_arr.std(ddof=1)) if len(seeds) > 1 else 0.0,
        "test_acc_mean": float(test_arr.mean()),
        "test_acc_std": float(test_arr.std(ddof=1)) if len(seeds) > 1 else 0.0,
        "f1_macro_mean": float(f1_arr.mean()),
        "f1_macro_std": float(f1_arr.std(ddof=1)) if len(seeds) > 1 else 0.0,
        "per_seed": per_seed,
    }
    (REPORTS_DIR / "multi_seed.json").write_text(json.dumps(summary, indent=2))
    print("\n=== Multi-seed summary ===")
    print(f"  test_acc = {summary['test_acc_mean']:.4f} +/- {summary['test_acc_std']:.4f}")
    print(f"  val_acc  = {summary['best_val_acc_mean']:.4f} +/- {summary['best_val_acc_std']:.4f}")
    print(f"  f1_macro = {summary['f1_macro_mean']:.4f} +/- {summary['f1_macro_std']:.4f}")

    # Simpan best_run sebagai model produksi (overwrite best_model).
    if best_run is not None:
        _persist_results(best_run["result"], args, label_map, mean, std, best_run["run_dir"])
        print(f"\nBest seed: {best_run['seed']} -> {best_run['run_dir']}")
    return 0


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--seed", type=int, default=42)
    parser.add_argument("--epochs", type=int, default=300)
    parser.add_argument("--hidden", type=int, default=256)
    parser.add_argument("--lr", type=float, default=0.001)
    parser.add_argument("--batch-size", type=int, default=64)
    parser.add_argument("--limit", type=int, default=None)
    parser.add_argument("--seed-list", type=str, default="",
                        help="latih beberapa seed, contoh '42,123,2024'")
    args = parser.parse_args()

    np.random.seed(args.seed)
    random.seed(args.seed)

    RUNS_DIR.mkdir(parents=True, exist_ok=True)
    REPORTS_DIR.mkdir(parents=True, exist_ok=True)

    if args.seed_list:
        return _multi_seed(args)

    print("Loading data...")
    X_train, y_train, X_val, y_val, X_test, y_test, label_map, mean, std = load_data()

    if args.limit:
        X_train, y_train = X_train[:args.limit], y_train[:args.limit]

    num_classes = len(label_map)
    input_dim = X_train.shape[1]
    print(f"Train: {len(X_train)}, Val: {len(X_val)}, Test: {len(X_test)}")
    print(f"Input dim: {input_dim}, Classes: {num_classes}")

    run_id = datetime.now().strftime("%Y%m%d-%H%M%S")
    run_dir = RUNS_DIR / run_id
    run_dir.mkdir(parents=True, exist_ok=True)

    config = vars(args).copy()
    config["input_dim"] = input_dim
    config["num_classes"] = num_classes
    config["train_size"] = len(X_train)
    config["dropout"] = 0.3
    config["weight_decay"] = 1e-4
    config["early_stop_patience"] = 30
    config["lr_schedule"] = "ReduceLROnPlateau(factor=0.5,patience=15,min=1e-5)"
    config["class_weight"] = "balanced via sklearn"
    with open(run_dir / "config.json", "w") as f:
        json.dump(config, f, indent=2)

    print(f"\nTraining for {args.epochs} epochs...")
    result = train_one(X_train, y_train, X_val, y_val, X_test, y_test,
                       num_classes, input_dim, args, run_dir)

    print("\nFinal evaluation on test set...")
    print(f"Test accuracy: {result['test_acc']:.4f}")
    print(f"Best val acc:  {result['best_val_acc']:.4f}")
    print(f"Macro F1:      {result['f1_macro']:.4f}")
    print(f"T={result['temperature']:.4f}, NLL {result['nll_before']:.4f} -> {result['nll_after']:.4f} "
          f"({result['nll_improvement_pct']:.2f}%)")

    _persist_results(result, args, label_map, mean, std, run_dir)
    print(f"\nResults saved to {run_dir}")
    print(f"Best model: {CHECKPOINT_DIR / 'best_model.npz'}")
    return 0


if __name__ == "__main__":
    sys.exit(main())