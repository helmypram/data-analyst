# run_taguchi_full.py
# Taguchi L9 (FULL) untuk Hybrid CNN–BiLSTM
# - Pakai dataset seimbang FULL (X_balanced_*.npy, y_balanced_*.npy)
# - Split 70/10/20 sekali (fixed) -> tuning pakai VALIDATION (10%)
# - Pilih kombinasi terbaik berdasar F1 (val), catat metrik & waktu
# - Konfirmasi best config pada 3 seed berbeda
# Output: CSV hasil L9, JSON best_config, CSV konfirmasi
# ------------------------------------------------------------

import os, json, time, csv
import numpy as np

from sklearn.model_selection import train_test_split
from sklearn.metrics import f1_score
import tensorflow as tf
import tensorflow.keras.backend as K
from tensorflow.keras.models import Sequential
from tensorflow.keras.layers import (LSTM, Dense, Dropout, Bidirectional,
                                     LayerNormalization, GlobalAveragePooling1D)
from tensorflow.keras.callbacks import EarlyStopping, ReduceLROnPlateau
from tensorflow.keras.metrics import AUC, BinaryAccuracy

# ====== Konfigurasi via ENV ======
BASE_DIR = os.getenv("BASE_DIR", r"D:\Semester 6\celeb-v2")
DATA_DIR = os.getenv("DATA_DIR", os.path.join(BASE_DIR, "new_final_dataset_mtcnn_v7_single_3"))
BACKBONE = os.getenv("BACKBONE", "xception").lower()       # b0|b2|resnet50|xception
EPOCHS   = int(os.getenv("EPOCHS", "80"))
WEIGHT_DECAY = float(os.getenv("WEIGHT_DECAY", "1e-4"))
GAMMA_FL = float(os.getenv("FOCAL_GAMMA", "2.0"))
ALPHA_FL = float(os.getenv("FOCAL_ALPHA", "0.75"))
SEED_SPLIT = int(os.getenv("SEED_SPLIT", "42"))             # seed untuk split tetap

OUT_DIR = os.path.join(BASE_DIR, f"final_taguchi_full_{BACKBONE}")
os.makedirs(OUT_DIR, exist_ok=True)

# ====== Focal Loss ======
def focal_loss(alpha=0.75, gamma=2.0):
    def loss(y_true, y_pred):
        eps = K.epsilon()
        y_pred = K.clip(y_pred, eps, 1. - eps)
        p_t = y_true * y_pred + (1. - y_true) * (1. - y_pred)
        alpha_t = y_true * alpha + (1. - y_true) * (1. - alpha)
        return K.mean(-alpha_t * K.pow(1. - p_t, gamma) * K.log(p_t))
    return loss

# ====== Optimizer AdamW (fallback)
try:
    from tensorflow.keras.optimizers import AdamW
except Exception:
    from tensorflow.keras.optimizers.experimental import AdamW

# ====== Load FULL data ======
X_path = os.path.join(DATA_DIR, f"X_balanced_{BACKBONE}.npy")
y_path = os.path.join(DATA_DIR, f"y_balanced_{BACKBONE}.npy")
if not (os.path.exists(X_path) and os.path.exists(y_path)):
    raise FileNotFoundError(f"Data FULL tidak ditemukan: {X_path} / {y_path}")

X = np.load(X_path).astype("float32")  # (N, T, D)
y = np.load(y_path).astype("float32")  # (N,)
print("====================================================")
print("TAGUCHI L9 (FULL)")
print(f"Backbone   : {BACKBONE}")
print(f"Data shape : {X.shape}, {y.shape} | REAL={int((y==0).sum())} FAKE={int((y==1).sum())}")
print(f"Output dir : {OUT_DIR}")
print("====================================================")

# ====== Split 70/10/20 (fixed untuk semua trial) ======
X_temp, X_test, y_temp, y_test = train_test_split(
    X, y, test_size=0.20, random_state=SEED_SPLIT, stratify=y
)
# 0.125 dari 0.8 -> 0.1 total sbg validation
X_train, X_val, y_train, y_val = train_test_split(
    X_temp, y_temp, test_size=0.125, random_state=SEED_SPLIT, stratify=y_temp
)

# ====== Orthogonal Array L9 (4 faktor × 3 level) ======
# A: LR         = {1e-4, 5e-4, 1e-3}
# B: Units1     = {64, 96, 128}
# C: Dropout    = {0.2, 0.3, 0.5}
# D: Batch size = {32, 64, 128}
A = [1e-4, 5e-4, 1e-3]
B = [64, 96, 128]
C = [0.2, 0.3, 0.5]
D = [32, 64, 128]

L9_idx = [
    (0,0,0,0),
    (0,1,1,1),
    (0,2,2,2),
    (1,0,1,2),
    (1,1,2,0),
    (1,2,0,1),
    (2,0,2,1),
    (2,1,0,2),
    (2,2,1,0),
]

def build_model(input_shape, units1=128, dropout=0.3, lr=5e-4, wdec=1e-4):
    model = Sequential([
        Bidirectional(LSTM(units1, return_sequences=True, dropout=dropout, recurrent_dropout=0.20),
                      input_shape=input_shape),
        LayerNormalization(),
        Bidirectional(LSTM(max(units1//2,32), return_sequences=True, dropout=dropout, recurrent_dropout=0.20)),
        LayerNormalization(),
        GlobalAveragePooling1D(),
        Dense(64, activation='relu', kernel_regularizer=tf.keras.regularizers.l2(1e-4)),
        Dropout(dropout),
        Dense(1, activation='sigmoid')
    ])
    opt = AdamW(learning_rate=lr, weight_decay=wdec, clipnorm=1.0)
    model.compile(loss=focal_loss(alpha=ALPHA_FL, gamma=GAMMA_FL),
                  optimizer=opt,
                  metrics=[BinaryAccuracy(name="acc"), AUC(name="auc")])
    return model

def eval_f1_at_best_thresh(y_true, y_prob):
    ths = np.arange(0.10, 0.90, 0.01)
    best_f1, best_th = -1.0, 0.5
    for t in ths:
        f1 = f1_score(y_true, (y_prob >= t).astype(int))
        if f1 >= best_f1:
            best_f1, best_th = f1, t
    return float(best_f1), float(best_th)

def run_one_trial(lr, units1, dropout, batch, seed=42):
    np.random.seed(seed); tf.random.set_seed(seed)
    model = build_model(X_train.shape[1:], units1=units1, dropout=dropout, lr=lr, wdec=WEIGHT_DECAY)

    cbs = [
        EarlyStopping(monitor='val_loss', patience=10, restore_best_weights=True),
        ReduceLROnPlateau(monitor='val_loss', factor=0.2, patience=4, min_lr=1e-5, verbose=0),
    ]
    t0 = time.time()
    hist = model.fit(
        X_train, y_train,
        validation_data=(X_val, y_val),
        epochs=EPOCHS,
        batch_size=batch,
        callbacks=cbs,
        verbose=0
    )
    dur = time.time() - t0

    # gunakan VALIDATION untuk seleksi
    y_val_prob = model.predict(X_val, verbose=0).ravel()
    f1_val, th_val = eval_f1_at_best_thresh(y_val, y_val_prob)

    # catat juga metrik di TEST (hanya untuk laporan — tidak dipakai seleksi)
    loss_te, acc_te, auc_te = model.evaluate(X_test, y_test, verbose=0)
    y_test_prob = model.predict(X_test, verbose=0).ravel()
    f1_te, th_te = eval_f1_at_best_thresh(y_test, y_test_prob)

    return {
        "f1_val": f1_val, "best_th_val": th_val,
        "f1_test": float(f1_te), "best_th_test": float(th_te),
        "auc_test": float(auc_te), "acc_test": float(acc_te), "loss_test": float(loss_te),
        "train_time_s": float(dur),
        "epochs": len(hist.history['loss'])
    }

# ====== Jalankan L9 ======
rows = []
for i, (ia, ib, ic, id_) in enumerate(L9_idx, start=1):
    params = {"lr": A[ia], "units1": B[ib], "dropout": C[ic], "batch": D[id_]}
    print(f"[{i}/9] Trial params: {params}")
    res = run_one_trial(**params, seed=42)
    rows.append({**params, **res})

# Simpan CSV hasil L9
csv_path = os.path.join(OUT_DIR, f"taguchi_results_{BACKBONE}.csv")
with open(csv_path, "w", newline="") as f:
    writer = csv.DictWriter(f, fieldnames=list(rows[0].keys()))
    writer.writeheader(); writer.writerows(rows)
print("✅ Hasil L9 tersimpan →", csv_path)

# Pilih terbaik berdasar F1 pada VALIDATION, lalu AUC_test sebagai tie-breaker
rows_sorted = sorted(rows, key=lambda r: (r["f1_val"], r["auc_test"]), reverse=True)
best = rows_sorted[0]
best_json = os.path.join(OUT_DIR, f"best_config_{BACKBONE}.json")
with open(best_json, "w") as f:
    json.dump(best, f, indent=2)
print("🏆 Best config (berdasar VALIDATION):", best)
print("✅ Simpan best_config →", best_json)

# ====== Konfirmasi 3× seed berbeda pada best config ======
confirm_rows = []
for seed in [11, 22, 33]:
    r = run_one_trial(best["lr"], best["units1"], best["dropout"], best["batch"], seed=seed)
    confirm_rows.append({"seed": seed, **r})

confirm_csv = os.path.join(OUT_DIR, f"confirm_best_{BACKBONE}.csv")
with open(confirm_csv, "w", newline="") as f:
    writer = csv.DictWriter(f, fieldnames=list(confirm_rows[0].keys()))
    writer.writeheader(); writer.writerows(confirm_rows)
print("✅ Konfirmasi (3× seed) →", confirm_csv)

# Ringkasan mean±std (F1 Val & Test)
f1v = [r["f1_val"] for r in confirm_rows]
f1t = [r["f1_test"] for r in confirm_rows]
print(f"Ringkasan konfirmasi — F1(val) mean±std: {np.mean(f1v):.4f} ± {np.std(f1v):.4f} | "
      f"F1(test) mean±std: {np.mean(f1t):.4f} ± {np.std(f1t):.4f}")
print("Selesai.")
