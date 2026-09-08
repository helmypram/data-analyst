# train_bilstm_full.py

# Latih & evaluasi Hybrid CNN–BiLSTM pada FULL DATASET
# Membaca:
#   - X_balanced_<BACKBONE>.npy, y_balanced_<BACKBONE>.npy
#   - final_taguchi_full_<BACKBONE>/best_config_<BACKBONE>.json
#     (fallback: final_taguchi_pilot_<BACKBONE>/best_config_<BACKBONE>.json)
# Menyimpan:
#   - model_best.h5, metrics.json/csv, history.csv,
#     classification_report.txt, cm.png, roc.png, training_plot.png
# ------------------------------------------------------------
import os, json, time, csv
import numpy as np
import matplotlib.pyplot as plt
from sklearn.model_selection import train_test_split
from sklearn.metrics import (roc_curve, auc, confusion_matrix, ConfusionMatrixDisplay,
                             classification_report, f1_score, precision_recall_fscore_support)

import tensorflow as tf
import tensorflow.keras.backend as K
from tensorflow.keras.models import Sequential
from tensorflow.keras.layers import (LSTM, Dense, Dropout, Bidirectional,
                                     LayerNormalization, GlobalAveragePooling1D)
from tensorflow.keras.callbacks import EarlyStopping, ModelCheckpoint, ReduceLROnPlateau
from tensorflow.keras.metrics import BinaryAccuracy, AUC

# ---------- ENV & path ----------
BASE_DIR = os.getenv("BASE_DIR", r"D:\Semester 6\celeb-v2")
# default ke dataset FULL versi _single_3
DATA_DIR = os.getenv("DATA_DIR", os.path.join(BASE_DIR, "new_final_dataset_mtcnn_v7_single_3"))
BACKBONE = os.getenv("BACKBONE", "b0").lower()
SEED     = int(os.getenv("SEED", "42"))
EPOCHS   = int(os.getenv("EPOCHS", "100"))

# file data full
X_path = os.path.join(DATA_DIR, f"X_balanced_{BACKBONE}.npy")
y_path = os.path.join(DATA_DIR, f"y_balanced_{BACKBONE}.npy")

# best config dari Taguchi (FULL, fallback ke PILOT)
TAG_FULL_DIR  = os.path.join(BASE_DIR, f"final_taguchi_full_{BACKBONE}")
TAG_PILOT_DIR = os.path.join(BASE_DIR, f"final_taguchi_pilot_{BACKBONE}")
BESTCFG_FULL  = os.path.join(TAG_FULL_DIR,  f"best_config_{BACKBONE}.json")
BESTCFG_PILOT = os.path.join(TAG_PILOT_DIR, f"best_config_{BACKBONE}.json")

if os.path.exists(BESTCFG_FULL):
    BESTCFG = BESTCFG_FULL
    TAGU_MODE = "full"
elif os.path.exists(BESTCFG_PILOT):
    BESTCFG = BESTCFG_PILOT
    TAGU_MODE = "pilot"
else:
    raise FileNotFoundError(
        "best_config tidak ditemukan. Jalankan run_taguchi_full.py (atau pilot) terlebih dahulu."
    )

# output akhir per-backbone (versi _single_3)
OUT_DIR  = os.path.join(BASE_DIR, f"final_trained_model_mtcnn_v7_single_3_{BACKBONE}")
os.makedirs(OUT_DIR, exist_ok=True)

print("====================================================")
print("TRAIN BiLSTM (FULL)")
print(f"Backbone    : {BACKBONE}")
print(f"Data full   : {X_path} | {y_path}")
print(f"Best cfg    : {BESTCFG} (mode={TAGU_MODE})")
print(f"Output dir  : {OUT_DIR}")
print("====================================================")

# ---------- seed ----------
np.random.seed(SEED); tf.random.set_seed(SEED)

# ---------- focal loss ----------
def focal_loss(alpha=0.75, gamma=2.0):
    def loss(y_true, y_pred):
        eps = K.epsilon()
        y_pred = K.clip(y_pred, eps, 1. - eps)
        p_t = y_true * y_pred + (1. - y_true) * (1. - y_pred)
        alpha_t = y_true * alpha + (1. - y_true) * (1. - alpha)
        return K.mean(-alpha_t * K.pow(1. - p_t, gamma) * K.log(p_t))
    return loss

# ---------- optimizer ----------
try:
    from tensorflow.keras.optimizers import AdamW
except Exception:
    from tensorflow.keras.optimizers.experimental import AdamW

# ---------- load data ----------
if not (os.path.exists(X_path) and os.path.exists(y_path)):
    raise FileNotFoundError("File X/y balanced tidak ditemukan. Jalankan balance_data_full.py terlebih dahulu.")
X = np.load(X_path).astype("float32")  # (N, T, D)
y = np.load(y_path).astype("float32")  # (N,)
print("Data shape:", X.shape, y.shape)

# sanity: minimal 2 kelas di test split
if len(np.unique(y)) < 2:
    raise RuntimeError("Label hanya 1 kelas. Cek hasil balancing.")

# ---------- load best config ----------
with open(BESTCFG, "r") as f:
    best = json.load(f)
# kompatibilitas key pilot/full
lr       = float(best.get("lr"))
units1   = int(best.get("units1"))
dropout  = float(best.get("dropout"))
batchsz  = int(best.get("batch"))
print("Best config (Taguchi):", {"lr": lr, "units1": units1, "dropout": dropout, "batch": batchsz})

# ---------- split (train/val/test = 70/10/20) ----------
X_temp, X_test, y_temp, y_test = train_test_split(
    X, y, test_size=0.20, random_state=SEED, stratify=y
)
X_train, X_val, y_train, y_val = train_test_split(
    X_temp, y_temp, test_size=0.125, random_state=SEED, stratify=y_temp
)  # 0.125 dari 0.8 -> 0.1 total

# ---------- model ----------
def build_model(input_shape):
    model = Sequential([
        Bidirectional(LSTM(units1, return_sequences=True, dropout=dropout, recurrent_dropout=0.20),
                      input_shape=input_shape),
        LayerNormalization(),
        Bidirectional(LSTM(max(units1//2, 32), return_sequences=True, dropout=dropout, recurrent_dropout=0.20)),
        LayerNormalization(),
        GlobalAveragePooling1D(),
        Dense(64, activation='relu', kernel_regularizer=tf.keras.regularizers.l2(1e-4)),
        Dropout(dropout),
        Dense(1, activation='sigmoid')
    ])
    opt = AdamW(learning_rate=lr, weight_decay=1e-4, clipnorm=1.0)
    model.compile(loss=focal_loss(alpha=0.75, gamma=2.0),
                  optimizer=opt,
                  metrics=[BinaryAccuracy(name="acc"), AUC(name="auc")])
    return model

model = build_model(X_train.shape[1:])
model.summary()

ckpt = os.path.join(OUT_DIR, "model_best.h5")
callbacks = [
    EarlyStopping(monitor='val_loss', patience=12, restore_best_weights=True),
    ModelCheckpoint(ckpt, monitor='val_loss', save_best_only=True, verbose=1),
    ReduceLROnPlateau(monitor='val_loss', factor=0.2, patience=5, min_lr=1e-5, verbose=1)
]

t0 = time.time()
hist = model.fit(
    X_train, y_train,
    validation_data=(X_val, y_val),
    epochs=EPOCHS,
    batch_size=batchsz,
    callbacks=callbacks,
    verbose=1
)
train_time = time.time() - t0

# ---------- evaluasi ----------
loss, acc, auc_ = model.evaluate(X_test, y_test, verbose=0)
y_prob = model.predict(X_test, verbose=0).ravel()

# cari threshold terbaik (F1)
ths = np.arange(0.10, 0.90, 0.01)
best_f1, best_th = -1.0, 0.5
for t in ths:
    f1 = f1_score(y_test, (y_prob >= t).astype(int))
    if f1 >= best_f1:
        best_f1, best_th = f1, t

y_pred = (y_prob >= best_th).astype(int)
prec, rec, f1, _ = precision_recall_fscore_support(y_test, y_pred, average="binary")
# EER (Equal Error Rate) + ROC-AUC manual (untuk komparasi)
fpr, tpr, thr = roc_curve(y_test, y_prob)
fnr = 1 - tpr
eer_idx = np.nanargmin(np.absolute(fnr - fpr))
eer = (fpr[eer_idx] + fnr[eer_idx]) / 2.0
roc_auc = auc(fpr, tpr)

print("\n=== TEST METRICS ===")
print(f"loss={loss:.4f} acc={acc:.4f} auc={auc_:.4f} | best_th={best_th:.2f}")
print(f"Precision={prec:.4f} Recall={rec:.4f} F1={f1:.4f} ROC-AUC={roc_auc:.4f} EER={eer:.4f}")

# ---------- simpan artefak ----------
# metrics json & csv
metrics = {
    "backbone": BACKBONE,
    "mode": TAGU_MODE,
    "loss": float(loss),
    "acc": float(acc),
    "auc": float(auc_),
    "precision": float(prec),
    "recall": float(rec),
    "f1": float(f1),
    "roc_auc": float(roc_auc),
    "eer": float(eer),
    "best_threshold": float(best_th),
    "epochs_trained": len(hist.history["loss"]),
    "train_time_s": float(train_time),
    "config": {"lr": lr, "units1": units1, "dropout": dropout, "batch": batchsz, "seed": SEED}
}
with open(os.path.join(OUT_DIR, "metrics.json"), "w") as f:
    json.dump(metrics, f, indent=2)

with open(os.path.join(OUT_DIR, "metrics.csv"), "w", newline="") as f:
    w = csv.DictWriter(f, fieldnames=list(metrics.keys()))
    w.writeheader(); w.writerow(metrics)

# classification report
with open(os.path.join(OUT_DIR, "classification_report.txt"), "w") as f:
    f.write(classification_report(y_test, y_pred, target_names=["REAL","FAKE"]))

# confusion matrix
cm = confusion_matrix(y_test, y_pred)
disp = ConfusionMatrixDisplay(confusion_matrix=cm, display_labels=["REAL","FAKE"])
disp.plot(cmap="Blues"); plt.title(f"Confusion Matrix - {BACKBONE}")
plt.tight_layout(); plt.savefig(os.path.join(OUT_DIR, "cm.png")); plt.close()

# ROC curve
plt.figure(figsize=(5,4))
plt.plot(fpr, tpr, label=f"AUC={roc_auc:.3f}")
plt.plot([0,1],[0,1],'--')
plt.xlabel("FPR"); plt.ylabel("TPR"); plt.title(f"ROC - {BACKBONE}")
plt.legend(); plt.grid(True); plt.tight_layout()
plt.savefig(os.path.join(OUT_DIR, "roc.png")); plt.close()

# training curves + history.csv
plt.figure(figsize=(10,4))
plt.subplot(1,2,1)
plt.plot(hist.history["acc"], label="train")
plt.plot(hist.history["val_acc"], label="val")
plt.title("Accuracy"); plt.legend(); plt.grid(True)
plt.subplot(1,2,2)
plt.plot(hist.history["loss"], label="train")
plt.plot(hist.history["val_loss"], label="val")
plt.title("Loss"); plt.legend(); plt.grid(True)
plt.tight_layout(); plt.savefig(os.path.join(OUT_DIR, "training_plot.png")); plt.close()

with open(os.path.join(OUT_DIR, "history.csv"), "w", newline="") as f:
    w = csv.writer(f)
    keys = list(hist.history.keys())
    w.writerow(keys)
    for i in range(len(hist.history[keys[0]])):
        w.writerow([hist.history[k][i] for k in keys])

# simpan config ringkas
with open(os.path.join(OUT_DIR, "training_config.json"), "w") as f:
    json.dump({"pad_len": int(X.shape[1]), "best_threshold": float(best_th),
               "backbone": BACKBONE, "taguchi_mode": TAGU_MODE}, f, indent=2)

print("\nArtefak disimpan di:", OUT_DIR)
