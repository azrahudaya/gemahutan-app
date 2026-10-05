#!/usr/bin/env python3
"""Train MLP classifier with OneVsRestClassifier + CalibratedClassifierCV.
For ML_09 S5 - Kepala Sigmoid.
"""
import argparse
import json
import sys
from pathlib import Path

import numpy as np
from sklearn.calibration import CalibratedClassifierCV
from sklearn.linear_model import LogisticRegression
from sklearn.multiclass import OneVsRestClassifier

# Local imports
sys.path.insert(0, str(Path(__file__).parent.parent))
from ml.train import accuracy, load_data, macro_f1

EMB_DIR = Path(__file__).parent / "embeddings"
CHECKPOINT_DIR = Path(__file__).parent / "checkpoints"
RUNS_DIR = Path(__file__).parent / "runs"
SPLITS_FILE = Path(__file__).parent / "data" / "splits.json"

def train_ovr_model(X_train, y_train, X_val, y_val, X_test, y_test, n_classes, input_dim, args):
    """Train with OneVsRestClassifier + CalibratedClassifierCV."""
    
    # Use LogisticRegression as base estimator
    base_clf = LogisticRegression(max_iter=1000, C=1.0)
    
    # OneVsRestClassifier for multilabel
    ovr_clf = OneVsRestClassifier(base_clf, n_jobs=-1)
    
    # CalibratedClassifierCV for probability calibration
    calibrated_clf = CalibratedClassifierCV(ovr_clf, method='sigmoid', cv=5)
    
    # Fit
    calibrated_clf.fit(X_train, y_train)
    
    # Predict
    y_pred = calibrated_clf.predict(X_test)

    # Probabilitas per kelas. CalibratedClassifierCV(method='sigmoid') sudah
    # mengkalibrasi tiap kepala sendiri, jadi TIDAK ada temperature/bias
    # tambahan di sini -- itu resep untuk softmax multikelas, bukan untuk
    # kepala sigmoid satu-lawan-sisa.
    y_proba = calibrated_clf.predict_proba(X_test)

    test_acc = accuracy(y_pred, y_test)
    f1 = macro_f1(y_test, y_pred, n_classes)

    return {
        "test_acc": test_acc,
        "f1_macro": f1,
        "model": calibrated_clf,
        "proba_test": y_proba,
    }

def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--seed", type=int, default=42)
    parser.add_argument("--epochs", type=int, default=100)
    args = parser.parse_args()
    
    np.random.seed(args.seed)
    
    RUNS_DIR.mkdir(parents=True, exist_ok=True)
    
    print("Loading data...")
    X_train, y_train, X_val, y_val, X_test, y_test, label_map, mean, std = load_data()
    
    num_classes = len(label_map)
    input_dim = X_train.shape[1]
    print(f"Train: {len(X_train)}, Val: {len(X_val)}, Test: {len(X_test)}")
    print(f"Input dim: {input_dim}, Classes: {num_classes}")
    
    run_id = f"ovr_calibrated_{args.seed}"
    run_dir = RUNS_DIR / run_id
    run_dir.mkdir(parents=True, exist_ok=True)
    
    print("Training OneVsRest + Calibrated model...")
    result = train_ovr_model(X_train, y_train, X_val, y_val, X_test, y_test, num_classes, input_dim, args)
    
    print(f"Test accuracy: {result['test_acc']:.4f}")
    print(f"Macro F1: {result['f1_macro']:.4f}")
    
    # CATATAN: versi sebelumnya menulis best_model.npz berisi NOL SEMUA di
    # sini sambil melaporkan akurasi dari model sklearn. Itu checkpoint palsu
    # dan sudah dihapus. Serialisasi kepala sigmoid ke format npz produksi
    # belum ada, jadi skrip ini SEMENTARA hanya melaporkan angka, tidak
    # menyimpan model yang bisa dipromosikan.
    results = {
        "test_acc": result["test_acc"],
        "f1_macro": result["f1_macro"],
        "run_id": run_id,
    }
    
    with open(run_dir / "results.json", "w") as f:
        json.dump(results, f, indent=2)
    
    print(f"Results saved to {run_dir}")
    return 0

if __name__ == "__main__":
    sys.exit(main())
